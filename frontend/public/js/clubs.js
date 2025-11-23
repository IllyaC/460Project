function buildJoinClubMessage(res, body){
  const detail = normalizeDetail(body);
  if(res.ok){
    return { message: "You joined this club.", type: "success" };
  }
  if(detail.includes("already") && detail.includes("member")){
    return { message: "You’re already a member of this club.", type: "info" };
  }
  if(detail.includes("pending")){
    return { message: "Your join request is pending approval.", type: "info" };
  }
  return { message: "We couldn’t process your join request right now.", type: "error" };
}

let createClubSubmitting = false;

function renderClubs(clubs){
  const ul = document.getElementById("club_list");
  ul.innerHTML = "";
  if(clubs.length === 0){
    ul.innerHTML = '<li class="empty-state">No clubs match your search.</li>';
    return;
  }

  clubs.forEach(club => {
    const li = document.createElement("li");
    li.classList.add("club-card");
    const categoryLabel = club.category ? `<span class="pill pill-muted">${club.category}</span>` : '<span class="pill pill-muted">General</span>';
    const memberCopy = club.member_count === 1 ? "Member" : "Members";
    const eventCopy = club.upcoming_event_count === 1 ? "Upcoming Event" : "Upcoming Events";
    li.innerHTML = `
        <div class="club-card__header">
          <div>
            <h4 class="club-card__title">${club.name}</h4>
            <p class="club-card__description">${club.description}</p>
            <div class="club-card__meta">${categoryLabel}
              <span class="pill pill-muted">${club.member_count} ${memberCopy}</span>
              <span class="pill pill-muted">${club.upcoming_event_count} ${eventCopy}</span>
            </div>
          </div>
        </div>
      `;
    const action = document.createElement("div");
    action.classList.add("club-card__actions");
    const status = clubMemberships.get(club.id);
    const statusCopy = status === "approved" ? "You are a member" : status === "pending" ? "Request pending" : "Not a member";
    const statusText = document.createElement("p");
    statusText.classList.add("hint", "club-card__status");
    statusText.textContent = statusCopy;
    const btn = document.createElement("button");
    btn.classList.add("club-card__cta");
    if(status === "approved"){
      btn.textContent = "Leave";
      btn.onclick = () => leaveClub(club.id);
    } else if(status === "pending"){
      btn.textContent = "Pending";
      btn.disabled = true;
    } else {
      btn.textContent = "Join";
      btn.onclick = () => joinClub(club.id);
    }
    action.appendChild(btn);
    action.appendChild(statusText);
    li.appendChild(action);
    ul.appendChild(li);
  });
}

async function loadClubs(){
  try {
    const res = await apiGetClubs();
    if(!res.ok){
      const body = await readJson(res);
      setStatus("clubs_status", `Failed to load clubs: ${buildErrorMessage(res, body)}`, "error");
      document.getElementById("club_list").innerHTML = '<li>Unable to load clubs right now.</li>';
      return;
    }
    const data = await res.json();
    allClubs = data;
    clubMemberships = new Map(data.map(club => [club.id, club.membership_status]));
    clubRoles = new Map(data.map(club => [club.id, club.membership_role]));
    filterClubList();
  } catch (err){
    setStatus("clubs_status", "Failed to load clubs.", "error");
    document.getElementById("club_list").innerHTML = '<li>Unable to load clubs right now.</li>';
  }
}

function renderMyClubs(){
  const ul = document.getElementById("my_club_list");
  ul.innerHTML = "";
  if(myClubs.length === 0){
    ul.innerHTML = '<li>No approved club memberships for this user yet.</li>';
    return;
  }
  myClubs.forEach(club => {
    const li = document.createElement("li");
    li.textContent = `${club.name} — ${club.description}`;
    ul.appendChild(li);
  });
}

async function loadMyClubs(){
  try {
    const res = await apiGetMyClubs();
    if(!res.ok){
      myClubs = [];
      setStatus("clubs_status", "Failed to load your clubs.", "error");
    } else {
      myClubs = await res.json();
      clearStatus("clubs_status");
    }
  } catch (err){
    console.error("Failed to load my clubs", err);
    myClubs = [];
    setStatus("clubs_status", "Failed to load your clubs.", "error");
  }
  renderMyClubs();
}

async function createClub(){
  if(createClubSubmitting){ return; }
  const nameInput = document.getElementById("club_name");
  const descInput = document.getElementById("club_desc");
  const submitBtn = document.getElementById("club_submit_btn");
  const name = nameInput?.value.trim() ?? "";
  const description = descInput?.value.trim() ?? "";
  if(!name || !description){
    const message = "Name and description are required to create a club.";
    showStatus("clubs_status", message, "error");
    showStatus("club_create_result", message, "error");
    return;
  }

  createClubSubmitting = true;
  const defaultLabel = submitBtn?.textContent;
  if(submitBtn){
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting…";
  }
  showStatus("clubs_status", "Submitting club for approval...", "info");
  showStatus("club_create_result", "Submitting club for approval...", "info");

  try {
    const res = await apiCreateClub({ name, description });
    const body = await readJson(res);
    if(res.ok){
      const successMessage = "Club submitted for approval. An admin will review it shortly.";
      showStatus("clubs_status", successMessage, "success");
      showStatus("club_create_result", successMessage, "success");
      if(nameInput){ nameInput.value = ""; }
      if(descInput){ descInput.value = ""; }
      await loadClubs();
      if(currentUser()?.role === "admin"){
        await loadPendingClubs();
      }
    } else {
      const errorMessage = `We couldn't submit your club: ${buildErrorMessage(res, body)}`;
      showStatus("clubs_status", errorMessage, "error");
      showStatus("club_create_result", errorMessage, "error");
    }
  } catch (err){
    const message = "We couldn't submit your club right now. Please try again.";
    showStatus("clubs_status", message, "error");
    showStatus("club_create_result", message, "error");
  } finally {
    if(submitBtn){
      submitBtn.disabled = false;
      submitBtn.textContent = defaultLabel ?? "Submit Club (Pending Approval)";
    }
    createClubSubmitting = false;
  }
}

async function joinClub(id){
  const clubId = id ?? Number(document.getElementById("join_club_id").value);
  if(!clubId){ return; }
  const res = await apiJoinClub(clubId);
  const body = await readJson(res);
  const joinMessage = buildJoinClubMessage(res, body);
  showStatus("clubs_status", joinMessage.message, joinMessage.type);
  showStatus("club_join_result", joinMessage.message, joinMessage.type);
  await loadClubs();
  await loadMyClubs();
}

async function leaveClub(id){
  if(!id){ return; }
  const res = await apiLeaveClub(id);
  const leaveMessage = res.ok
    ? { message: "You have left the club.", type: "success" }
    : { message: "We couldn’t update your club membership right now.", type: "error" };
  showStatus("clubs_status", leaveMessage.message, leaveMessage.type);
  showStatus("club_join_result", leaveMessage.message, leaveMessage.type);
  await loadClubs();
  await loadMyClubs();
}

function filterClubList(){
  const search = document.getElementById("club_search")?.value.trim().toLowerCase() ?? "";
  const filtered = !search
    ? allClubs
    : allClubs.filter(club =>
        club.name.toLowerCase().includes(search) ||
        club.description.toLowerCase().includes(search)
      );
  renderClubs(filtered);
}

async function loadClubDetail(){
  const id = Number(document.getElementById("club_detail_id").value);
  if(!id){
    setStatus("club_detail_status", "Enter a club ID to load.", "error");
    return;
  }
  let res;
  try {
    res = await apiGetClubDetail(id);
  } catch (err){
    setStatus("club_detail_status", "Failed to load club details.", "error");
    document.getElementById("club_detail").textContent = "";
    return;
  }
  if(!res.ok){
    const body = await readJson(res);
    setStatus("club_detail_status", `Failed to load club: ${buildErrorMessage(res, body)}`, "error");
    document.getElementById("club_detail").textContent = "";
    return;
  }
  const data = await res.json();
  clearStatus("club_detail_status");
  loadedClubId = id;
  const div = document.getElementById("club_detail");
  const members = data.members.map(m => {
    const roleLabel = m.role.charAt(0).toUpperCase() + m.role.slice(1);
    const statusLabel = m.status.charAt(0).toUpperCase() + m.status.slice(1);
    return `<li class="member-row"><span class="member-email">${m.user_email}</span><span class="badge badge-role">${roleLabel}</span><span class="badge badge-status">${statusLabel}</span></li>`;
  }).join('');
  const announcements = data.announcements.map(a => {
    const date = new Date(a.created_at).toLocaleDateString();
    return `<li class="announcement-row"><span class="announcement-date">${date}</span> <strong>${a.title}</strong> — ${a.body} <button class="btn-ghost" onclick=\"flagAnnouncement(${a.id})\">Flag Content</button></li>`;
  }).join('');
  const user = currentUser();
  const isClubLeader = data.members.some(m => m.user_email === user?.email && m.role === "leader" && m.status === "approved");
  const canManageClubEvents = user?.role === "admin" || (user?.role === "leader" && user?.is_approved && isClubLeader);
  const events = data.events
    .map(ev => {
      const deleteBtn = canManageClubEvents ? ` <button class="btn-ghost" onclick="deleteEvent(${ev.id})">Delete</button>` : '';
      return `<li class="event-row"><div><strong>${ev.title}</strong><p class="hint">${new Date(ev.starts_at).toLocaleDateString()}</p></div><div class="event-meta">Cap ${ev.capacity} · ${ev.registration_count} registered</div>${deleteBtn}</li>`;
    })
    .join('');
  const overviewBadges = `
      <div class="club-detail__meta">
        <span class="pill">${data.club.member_count} Members</span>
        <span class="pill pill-muted">${data.club.upcoming_event_count} Upcoming Events</span>
      </div>`;
  div.innerHTML = `
      <div class="club-detail__section">
        <p class="eyebrow">Overview</p>
        <h3>${data.club.name} ${data.club.approved ? '' : '(Pending)'}</h3>
        <p class="club-detail__description">${data.club.description}</p>
        ${overviewBadges}
      </div>
      <div class="club-detail__grid">
        <div class="club-detail__section">
          <h4>Upcoming Events</h4>
          <ul class="stacked-list">${events || '<li class="hint">No upcoming events</li>'}</ul>
        </div>
        <div class="club-detail__section">
          <h4>Members</h4>
          <ul class="stacked-list">${members || '<li class="hint">No members listed</li>'}</ul>
        </div>
        <div class="club-detail__section">
          <h4>Announcements</h4>
          <ul class="stacked-list">${announcements || '<li class="hint">No announcements</li>'}</ul>
        </div>
      </div>
    `;

  const pendingMembers = data.members.filter(m => m.status === "pending");
  const pendingList = document.getElementById("pending_members_list");
  if(pendingList){
    pendingList.innerHTML = pendingMembers.length
      ? pendingMembers.map(m => {
          const roleLabel = m.role.charAt(0).toUpperCase() + m.role.slice(1);
          return `<li class="member-row"><span class="member-email">${m.user_email}</span><span class="badge badge-role">${roleLabel}</span><button class="btn-secondary" onclick=\"approveMember('${m.user_email}')\">Approve</button></li>`;
        }).join('')
      : '<li class="hint">No pending requests.</li>';
  }

  const announcementList = document.getElementById("leader_announcements_list");
  if(announcementList){
    announcementList.innerHTML = data.announcements.length
      ? data.announcements.map(a => {
          const date = new Date(a.created_at).toLocaleDateString();
          return `<li class="announcement-row"><span class="announcement-date">${date}</span><strong>${a.title}</strong><span>${a.body}</span></li>`;
        }).join('')
      : '<li class="hint">No announcements yet.</li>';
  }

  const leaderDashboard = document.getElementById("leader_dashboard");
  if(leaderDashboard){
    const shouldShowLeaderTools = user?.role === "admin" || (user?.role === "leader" && user?.is_approved && isClubLeader);
    leaderDashboard.classList.toggle("hidden", !shouldShowLeaderTools);
  }
}

async function approveMember(emailOverride){
  if(!loadedClubId){ setStatus('club_detail_status', 'Load a club first.', 'error'); return; }
  const email = emailOverride ?? document.getElementById("approve_email").value;
  const res = await apiApproveMember(loadedClubId, email);
  const body = await readJson(res);
  if(res.ok){
    setStatus("club_detail_status", "Member approved.", "success");
  } else {
    setStatus("club_detail_status", `Approve member failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadClubDetail();
}

async function postAnnouncement(){
  if(!loadedClubId){ setStatus('club_detail_status', 'Load a club first.', 'error'); return; }
  const payload = {
    title: document.getElementById("ann_title").value,
    body: document.getElementById("ann_body").value
  };
  const res = await apiPostAnnouncement(loadedClubId, payload);
  const body = await readJson(res);
  if(res.ok){
    setStatus("club_detail_status", "Announcement posted.", "success");
  } else {
    setStatus("club_detail_status", `Announcement failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadClubDetail();
}

async function createClubEvent(){
  if(!loadedClubId){ setStatus('club_detail_status', 'Load a club first.', 'error'); return; }
  const startsAt = requireDateTime("club_event_start", "club_detail_status");
  if(!startsAt){ return; }
  const payload = {
    title: document.getElementById("club_event_title").value,
    starts_at: startsAt,
    location: document.getElementById("club_event_location").value,
    capacity: Number(document.getElementById("club_event_capacity").value),
    price_cents: Number(document.getElementById("club_event_price").value),
    category: document.getElementById("club_event_category").value
  };
  const res = await apiCreateClubEvent(loadedClubId, payload);
  const body = await readJson(res);
  if(res.ok){
    setStatus("club_detail_status", "Club event created.", "success");
  } else {
    setStatus("club_detail_status", `Club event failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadClubDetail();
}

async function flagAnnouncement(id){
  const reason = prompt("Why are you flagging this announcement?");
  if(!reason){ return; }
  try {
    const res = await apiFlagItem({ item_type: "announcement", item_id: id, reason });
    const body = await readJson(res);
    if(res.ok){
      setStatus("club_detail_status", "Flag submitted.", "success");
    } else {
      setStatus("club_detail_status", `Flag failed: ${buildErrorMessage(res, body)}`, "error");
    }
  } catch (err){
    setStatus("club_detail_status", "Flag failed.", "error");
  }
}
