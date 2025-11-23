const API = "http://localhost:8000/api";

async function readJson(res){
  try {
    return await res.json();
  } catch (err){
    return null;
  }
}

function normalizeDetail(body){
  const detail = body?.detail || body?.error || body?.message;
  return typeof detail === "string" ? detail.toLowerCase() : "";
}

function buildErrorMessage(res, body){
  const detail = body?.detail || body?.error || body?.message;
  return detail ? `${detail} (status ${res.status})` : `Status ${res.status}`;
}

function buildHeaders(json=true){
  const headers = {};
  const user = currentUser();
  if(user?.id){ headers["X-User-Id"] = user.id; }
  if(user?.email){ headers["X-User-Email"] = user.email; }
  if(json){ headers["Content-Type"] = "application/json"; }
  return headers;
}

// Auth APIs
function apiRegisterUser(payload){
  return fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

function apiLoginUser(payload){
  return fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

// Events APIs
function apiGetEvents(params){
  return fetch(`${API}/events?${params.toString()}`);
}

function apiGetTrendingEvents(){
  return fetch(`${API}/events/trending`);
}

function apiCreateEvent(payload){
  return fetch(`${API}/events`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(payload)
  });
}

function apiDeleteEvent(eventId){
  return fetch(`${API}/events/${eventId}`, {
    method: "DELETE",
    headers: buildHeaders(false)
  });
}

function apiRegisterEvent(eventId){
  return fetch(`${API}/registrations`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify({ event_id: eventId })
  });
}

function apiUnregisterEvent(eventId){
  return fetch(`${API}/registrations/${eventId}`, {
    method: "DELETE",
    headers: buildHeaders(false)
  });
}

function apiGetMyRegistrations(){
  return fetch(`${API}/registrations/mine`, { headers: buildHeaders(false) });
}

// Club APIs
function apiGetClubs(){
  return fetch(`${API}/clubs`, { headers: buildHeaders(false) });
}

function apiGetMyClubs(){
  return fetch(`${API}/clubs/mine`, { headers: buildHeaders(false) });
}

function apiCreateClub(payload){
  return fetch(`${API}/clubs`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(payload)
  });
}

function apiJoinClub(clubId){
  return fetch(`${API}/clubs/${clubId}/join`, {
    method: "POST",
    headers: buildHeaders(true)
  });
}

function apiLeaveClub(clubId){
  return fetch(`${API}/clubs/${clubId}/leave`, {
    method: "POST",
    headers: buildHeaders(true)
  });
}

function apiGetClubDetail(clubId){
  return fetch(`${API}/clubs/${clubId}`, { headers: buildHeaders(false) });
}

function apiApproveMember(clubId, email){
  return fetch(`${API}/clubs/${clubId}/members/${encodeURIComponent(email)}/approve`, {
    method: "POST",
    headers: buildHeaders(true)
  });
}

function apiPostAnnouncement(clubId, payload){
  return fetch(`${API}/clubs/${clubId}/announcements`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(payload)
  });
}

function apiCreateClubEvent(clubId, payload){
  return fetch(`${API}/clubs/${clubId}/events`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(payload)
  });
}

// Flags and admin APIs
function apiFlagItem(item){
  return fetch(`${API}/flags`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify(item)
  });
}

function apiGetFlags(){
  return fetch(`${API}/admin/flags`, { headers: buildHeaders(false) });
}

function apiResolveFlag(id){
  return fetch(`${API}/admin/flags/${id}/resolve`, { method: "POST", headers: buildHeaders(false) });
}

function apiGetPendingClubs(){
  return fetch(`${API}/admin/clubs/pending`, { headers: buildHeaders(false) });
}

function apiApproveClub(id){
  return fetch(`${API}/admin/clubs/${id}/approve`, {
    method: "POST",
    headers: buildHeaders(false)
  });
}

function apiGetPendingLeaders(){
  return fetch(`${API}/admin/leaders/pending`, { headers: buildHeaders(false) });
}

function apiApproveLeader(id){
  return fetch(`${API}/admin/leaders/${id}/approve`, {
    method: "POST",
    headers: buildHeaders(false)
  });
}
