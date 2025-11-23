async function loadFlags(){
  if(personaRole !== "admin"){
    setStatus("admin_status", "Admin role required.", "error");
    return;
  }
  const tbody = document.getElementById("flagged_tbody");
  tbody.innerHTML = "";
  try {
    const res = await apiGetFlags();
    if(res.status === 403){
      setStatus("admin_status", "Admin role required.", "error");
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Admin role required.</td></tr>';
      return;
    }
    if(!res.ok){
      const body = await readJson(res);
      setStatus("admin_status", `Failed to load flags: ${buildErrorMessage(res, body)}`, "error");
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No flagged items found.</td></tr>';
      return;
    }
    const data = await res.json();
    if(data.length === 0){
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No flagged items found.</td></tr>';
      clearStatus("admin_status");
      return;
    }
    clearStatus("admin_status");
    data.forEach(flag => {
      const label = flag.item_type === "event" ? `Event #${flag.item_id}` : `Announcement #${flag.item_id}`;
      const reason = flag.reason || "No reason provided.";
      const tr = document.createElement("tr");
      tr.innerHTML = `
          <td class="pill-cell"><span class="pill pill-muted">${flag.item_type === "event" ? "Event" : "Announcement"}</span></td>
          <td>${label}</td>
          <td>${reason}</td>
          <td>${flag.user_email}</td>
          <td>${new Date(flag.created_at).toLocaleString()}</td>
          <td><button class="btn-secondary" onclick="resolveFlag(${flag.id})">Resolve</button></td>
        `;
      tbody.appendChild(tr);
    });
  } catch (err){
    setStatus("admin_status", "Failed to load flags.", "error");
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No flagged items found.</td></tr>';
  }
}

async function resolveFlag(id){
  if(personaRole !== "admin"){
    setStatus("admin_status", "Admin role required.", "error");
    return;
  }
  const res = await apiResolveFlag(id);
  if(res.ok){
    setStatus("admin_status", "Flag resolved successfully.", "success");
  } else {
    const body = await readJson(res);
    setStatus("admin_status", `Resolve failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadFlags();
}

async function loadPendingClubs(){
  if(personaRole !== "admin"){
    setStatus("pending_club_status", "Admin role required.", "error");
    return;
  }
  const tbody = document.getElementById("pending_club_tbody");
  tbody.innerHTML = "";
  try {
    const res = await apiGetPendingClubs();
    if(res.status === 403){
      setStatus("pending_club_status", "Admin role required.", "error");
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Admin role required.</td></tr>';
      return;
    }
    if(!res.ok){
      const body = await readJson(res);
      setStatus("pending_club_status", `Failed to load pending clubs: ${buildErrorMessage(res, body)}`, "error");
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No pending clubs.</td></tr>';
      return;
    }
    const data = await res.json();
    if(data.length === 0){
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No pending clubs.</td></tr>';
      clearStatus("pending_club_status");
      return;
    }
    clearStatus("pending_club_status");
    data.forEach(club => {
      const description = club.description || "No description provided.";
      const requester = club.created_by_email || "Unknown";
      const tr = document.createElement("tr");
      tr.innerHTML = `
          <td><div class="table-title">${club.name}</div><div class="muted">ID ${club.id}</div></td>
          <td>${description}</td>
          <td>${requester}</td>
          <td><button class="btn-secondary" onclick="approveClub(${club.id})">Approve</button></td>
        `;
      tbody.appendChild(tr);
    });
  } catch (err){
    setStatus("pending_club_status", "Failed to load pending clubs.", "error");
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No pending clubs.</td></tr>';
  }
}

async function approveClub(idOverride){
  if(personaRole !== "admin"){
    setStatus("pending_club_status", "Admin role required.", "error");
    return;
  }
  const id = typeof idOverride === "number" ? idOverride : null;
  if(!id){
    setStatus("pending_club_status", "Choose a club to approve.", "error");
    return;
  }
  const res = await apiApproveClub(id);
  const body = await readJson(res);
  if(res.ok){
    setStatus("pending_club_status", "Club approved successfully.", "success");
  } else {
    setStatus("pending_club_status", `Approve failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadClubs();
  loadPendingClubs();
}

async function loadPendingLeaders(){
  if(personaRole !== "admin"){
    setStatus("pending_leader_status", "Admin role required.", "error");
    return;
  }
  const tbody = document.getElementById("pending_leader_tbody");
  tbody.innerHTML = "";
  try {
    const res = await apiGetPendingLeaders();
    if(res.status === 403){
      setStatus("pending_leader_status", "Admin role required.", "error");
      tbody.innerHTML = '<tr><td colspan="3" class="empty-state">Admin role required.</td></tr>';
      return;
    }
    if(!res.ok){
      const body = await readJson(res);
      setStatus(
        "pending_leader_status",
        `Failed to load pending leaders: ${buildErrorMessage(res, body)}`,
        "error"
      );
      tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No pending leaders.</td></tr>';
      return;
    }
    const data = await res.json();
    if(data.length === 0){
      tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No pending leaders.</td></tr>';
      clearStatus("pending_leader_status");
      return;
    }
    clearStatus("pending_leader_status");
    data.forEach(leader => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
          <td><div class="table-title">${leader.username}</div><div class="muted">ID ${leader.id}</div></td>
          <td>${leader.email}</td>
          <td><button class="btn-secondary" onclick="approveLeader(${leader.id})">Approve</button></td>
        `;
      tbody.appendChild(tr);
    });
  } catch (err){
    setStatus("pending_leader_status", "Failed to load pending leaders.", "error");
    tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No pending leaders.</td></tr>';
  }
}

async function approveLeader(idOverride){
  if(personaRole !== "admin"){
    setStatus("pending_leader_status", "Admin role required.", "error");
    return;
  }
  const id = typeof idOverride === "number" ? idOverride : null;
  if(!id){
    setStatus("pending_leader_status", "Choose a leader to approve.", "error");
    return;
  }
  const res = await apiApproveLeader(id);
  const body = await readJson(res);
  if(res.ok){
    setStatus("pending_leader_status", "Leader approved successfully.", "success");
  } else {
    setStatus("pending_leader_status", `Approve failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadPendingLeaders();
}
