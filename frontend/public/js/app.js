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
  const user = currentUser();
  if(!user){
    summary.textContent = "";
    return;
  }
  const isLeader = user.role === "leader";
  const roleLabel = user.role === "admin" ? "Admin" : isLeader ? "Club Leader" : "Student";
  const approvalLabel = isLeader && !user.is_approved ? " • Pending approval" : "";
  const displayName = user.username ? `${user.username} • ` : "";
  summary.textContent = `${displayName}${user.email} (${roleLabel}${approvalLabel})`;
}

function showAuthTab(target){
  document.querySelectorAll(".auth-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.target === target);
  });
  document.getElementById("signup_panel")?.classList.toggle("hidden", target !== "signup");
  document.getElementById("login_panel")?.classList.toggle("hidden", target !== "login");
}

async function handleSignup(event){
  event?.preventDefault();
  const username = document.getElementById("signup_username").value.trim();
  const email = document.getElementById("signup_email").value.trim();
  const password = document.getElementById("signup_password").value;
  const desiredRole = document.getElementById("signup_role").value;
  if(!username || !email || !password){
    setStatus("signup_status", "All fields are required to create an account.", "error");
    return;
  }

  setStatus("signup_status", "Creating your account...", "info");
  try {
    const res = await apiRegisterUser({ username, email, password, desired_role: desiredRole });
    const body = await readJson(res);
    if(res.ok){
      const successMessage = desiredRole === "leader"
        ? "Account created. An admin must approve your leader role before you can manage clubs."
        : "Account created. You can now sign in.";
      setStatus("signup_status", successMessage, "success");
      document.getElementById("login_identifier").value = email || username;
      showAuthTab("login");
    } else {
      setStatus("signup_status", `Sign up failed: ${buildErrorMessage(res, body)}`, "error");
    }
  } catch (err){
    setStatus("signup_status", "Unable to sign up right now. Please try again.", "error");
  }
}

async function handleLogin(event){
  event?.preventDefault();
  const identifier = document.getElementById("login_identifier").value.trim();
  const password = document.getElementById("login_password").value;
  if(!identifier || !password){
    setStatus("login_status", "Username/email and password are required.", "error");
    return;
  }
  setStatus("login_status", "Signing you in...", "info");
  try {
    const res = await apiLoginUser({ username_or_email: identifier, password });
    const body = await readJson(res);
    if(res.ok){
      setUser(body);
      clearStatus("login_status");
      startSession();
    } else {
      setStatus("login_status", `Login failed: ${buildErrorMessage(res, body)}`, "error");
    }
  } catch (err){
    setStatus("login_status", "Unable to log in right now. Please try again.", "error");
  }
}

function signOut(event){
  event?.preventDefault();
  resetUser();
  resetSharedState();
  resetAppContent();
  document.getElementById("login_identifier").value = "";
  document.getElementById("login_password").value = "";
  document.getElementById("signup_username").value = "";
  document.getElementById("signup_email").value = "";
  document.getElementById("signup_password").value = "";
  document.getElementById("login_section").classList.remove("hidden");
  document.getElementById("app_shell").classList.add("hidden");
  document.getElementById("top_bar").classList.add("hidden");
  document.getElementById("role_notice").classList.add("hidden");
  showAuthTab("signup");
  updateRoleVisibility();
  updateUserSummary();
}

function startSession(){
  const user = currentUser();
  if(!user){ return; }
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
  if(user.role === "admin"){
    loadPendingClubs();
    loadPendingLeaders();
    loadFlags();
    loadAdminClubsOverview();
  }
}

function resetAppContent(){
  clearStatus("events_status");
  clearStatus("clubs_status");
  clearStatus("admin_status");
  clearStatus("pending_club_status");
  clearStatus("pending_leader_status");
  clearStatus("admin_club_overview_status");
  document.getElementById("events_list").innerHTML = "";
  document.getElementById("trending_list").innerHTML = "";
  document.getElementById("club_list").innerHTML = "";
  document.getElementById("club_name").value = "";
  document.getElementById("club_desc").value = "";
  document.getElementById("club_detail").innerHTML = "";
  document.getElementById("admin_club_overview_tbody").innerHTML = '<tr><td colspan="7" class="empty-state">Load all clubs to review their details.</td></tr>';
  document.getElementById("pending_club_tbody").innerHTML = '<tr><td colspan="4" class="empty-state">Load pending clubs to review submissions.</td></tr>';
  document.getElementById("pending_leader_tbody").innerHTML = '<tr><td colspan="3" class="empty-state">Load pending leaders to review requests.</td></tr>';
  document.getElementById("flagged_tbody").innerHTML = '<tr><td colspan="6" class="empty-state">Load flagged content to review reports.</td></tr>';
  document.getElementById("my_events_tbody").innerHTML = '<tr><td colspan="4">Log in above to load your registrations.</td></tr>';
  document.getElementById("my_club_list").innerHTML = '<li>Log in above to load your clubs.</li>';
}

function showNavSection(target){
  const groups = getSectionGroups();
  if(target === "admin" && currentUser()?.role !== "admin"){
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
  const user = currentUser();
  const role = user?.role ?? "";
  const leaderApproved = role === "leader" && user?.is_approved;
  document.querySelectorAll(".admin-only").forEach(el => {
    const hidden = role !== "admin";
    el.classList.toggle("hidden", hidden);
    el.setAttribute("aria-hidden", hidden);
  });
  document.querySelectorAll(".leader-only").forEach(el => {
    const hidden = role !== "admin" && !leaderApproved;
    el.classList.toggle("hidden", hidden);
    el.setAttribute("aria-hidden", hidden);
  });

  const roleNotice = document.getElementById("role_notice");
  if(role === "leader" && !leaderApproved){
    roleNotice.textContent = "Your leader account is pending admin approval.";
    roleNotice.classList.remove("hidden");
  } else {
    roleNotice.classList.add("hidden");
    roleNotice.textContent = "";
  }

  const activeNav = document.querySelector(".nav-button.active")?.dataset.target ?? "events";
  if(role !== "admin" && activeNav === "admin"){
    showNavSection("events");
  }
}

// initial data
resetAppContent();
updateRoleVisibility();
showNavSection("events");
showAuthTab("signup");
