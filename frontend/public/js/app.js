function getStatusElement(sectionId){
  return document.getElementById(sectionId) || document.getElementById(`${sectionId}_status`);
}

function showStatus(sectionId, message, type = "info"){
  const el = getStatusElement(sectionId);
  if(!el){ return; }
  el.textContent = message;
  el.className = `section-status status ${type}`;
  el.classList.toggle("visible", Boolean(message));
}

function setStatus(id, message, type = "info"){
  showStatus(id, message, type);
}

function clearStatus(id){
  showStatus(id, "");
}

function updateUserSummary(){
  const summary = document.getElementById("user_summary");
  if(!personaEmail){
    summary.textContent = "";
    return;
  }
  const displayRole = personaRole === "leader" ? "Club Leader" : personaRole.charAt(0).toUpperCase() + personaRole.slice(1);
  const displayName = personaName ? `${personaName} • ` : "";
  summary.textContent = `${displayName}${personaEmail} (${displayRole})`;
}

function handleLogin(){
  const name = document.getElementById("login_name").value.trim();
  const email = document.getElementById("login_email").value.trim();
  const role = document.getElementById("login_role").value;

  if(!name || !email){
    setStatus("login_status", "Name and email are required to continue.", "error");
    return;
  }

  setPersona(name, email, role);
  clearStatus("login_status");
  startSession();
}

function switchUser(event){
  event?.preventDefault();
  resetPersona();
  resetSharedState();
  resetAppContent();
  document.getElementById("login_name").value = "";
  document.getElementById("login_email").value = "";
  document.getElementById("login_role").value = "student";
  document.getElementById("login_section").classList.remove("hidden");
  document.getElementById("app_shell").classList.add("hidden");
  document.getElementById("top_bar").classList.add("hidden");
  updateRoleVisibility();
  updateUserSummary();
}

function startSession(){
  document.getElementById("login_section").classList.add("hidden");
  document.getElementById("app_shell").classList.remove("hidden");
  document.getElementById("top_bar").classList.remove("hidden");
  updateRoleVisibility();
  updateUserSummary();
  showNavSection("events");
  loadEvents();
  loadTrending();
  loadClubs();
  loadMyClubs();
  const clubDetailValue = document.getElementById("club_detail_id")?.value;
  if(clubDetailValue){
    loadClubDetail();
  }
  if(personaRole === "admin"){
    loadPendingClubs();
    loadPendingLeaders();
    loadFlags();
  }
}

function resetAppContent(){
  clearStatus("events_status");
  clearStatus("clubs_status");
  clearStatus("admin_status");
  clearStatus("pending_club_status");
  clearStatus("pending_leader_status");
  document.getElementById("events_list").innerHTML = "";
  document.getElementById("trending_list").innerHTML = "";
  document.getElementById("club_list").innerHTML = "";
  document.getElementById("club_name").value = "";
  document.getElementById("club_desc").value = "";
  document.getElementById("club_detail").innerHTML = "";
  document.getElementById("pending_club_tbody").innerHTML = '<tr><td colspan="4" class="empty-state">Load pending clubs to review submissions.</td></tr>';
  document.getElementById("pending_leader_tbody").innerHTML = '<tr><td colspan="3" class="empty-state">Load pending leaders to review requests.</td></tr>';
  document.getElementById("flagged_tbody").innerHTML = '<tr><td colspan="6" class="empty-state">Load flagged content to review reports.</td></tr>';
  document.getElementById("my_events_tbody").innerHTML = '<tr><td colspan="4">Log in above to load your registrations.</td></tr>';
  document.getElementById("my_club_list").innerHTML = '<li>Log in above to load your clubs.</li>';
}

function showNavSection(target){
  const groups = getSectionGroups();
  if(target === "admin" && personaRole !== "admin"){
    target = "events";
  }
  groups.forEach(group => {
    document.querySelectorAll(`[data-section-group="${group}"]`).forEach(section => {
      section.classList.toggle("hidden", group !== target);
    });
  });

  document.querySelectorAll(".nav-button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.target === target);
  });
}

function updateRoleVisibility(){
  const role = personaRole;
  document.querySelectorAll(".admin-only").forEach(el => {
    const hidden = role !== "admin";
    el.classList.toggle("hidden", hidden);
    el.setAttribute("aria-hidden", hidden);
  });
  document.querySelectorAll(".leader-only").forEach(el => {
    const hidden = role !== "leader" && role !== "admin";
    el.classList.toggle("hidden", hidden);
    el.setAttribute("aria-hidden", hidden);
  });

  const activeNav = document.querySelector(".nav-button.active")?.dataset.target ?? "events";
  if(role !== "admin" && activeNav === "admin"){
    showNavSection("events");
  }
}

// initial data
resetAppContent();
updateRoleVisibility();
showNavSection("events");
