function buildIsoString(dateStr, hourStr, minuteStr, ampm){
  if(!dateStr){ return null; }
  if(ampm !== "AM" && ampm !== "PM"){ return null; }
  const hour = Number(hourStr);
  const minute = Number(minuteStr);
  if(Number.isNaN(hour) || Number.isNaN(minute)){ return null; }
  if(hour < 1 || hour > 12 || minute < 0 || minute > 59){ return null; }
  const [year, month, day] = dateStr.split("-").map(Number);
  if([year, month, day].some(num => Number.isNaN(num))){ return null; }

  let hour24 = hour % 12;
  if(ampm === "PM" && hour !== 12){
    hour24 += 12;
  } else if(ampm === "AM" && hour === 12){
    hour24 = 0;
  }

  const iso = new Date(Date.UTC(year, month - 1, day, hour24, minute, 0, 0)).toISOString();
  return iso;
}

function getSearchDateTime(prefix){
  const date = document.getElementById(`${prefix}_date`)?.value;
  const hour = document.getElementById(`${prefix}_hour`)?.value;
  const minute = document.getElementById(`${prefix}_minute`)?.value;
  const ampm = document.getElementById(`${prefix}_ampm`)?.value;
  if(!date || !hour || !minute || !ampm){ return null; }
  return buildIsoString(date, hour, minute, ampm);
}

function requireDateTime(prefix, statusTarget){
  const date = document.getElementById(`${prefix}_date`)?.value;
  const hour = document.getElementById(`${prefix}_hour`)?.value;
  const minute = document.getElementById(`${prefix}_minute`)?.value;
  const ampm = document.getElementById(`${prefix}_ampm`)?.value;
  if(!date || !hour || !minute || !ampm){
    setStatus(statusTarget, "Please provide a complete date, time, and AM/PM.", "error");
    return null;
  }
  const iso = buildIsoString(date, hour, minute, ampm);
  if(!iso){
    setStatus(statusTarget, "Please enter a valid date and time.", "error");
    return null;
  }
  return iso;
}

function formatPrice(cents){
  if(cents === null || cents === undefined){ return "—"; }
  if(Number(cents) === 0){ return "Free"; }
  return `$${(Number(cents) / 100).toFixed(2)}`;
}

function buildRegistrationMessage(res, body){
  const detail = normalizeDetail(body);
  if(res.ok){
    return { message: "Registration successful.", type: "success" };
  }
  if(detail.includes("already") && detail.includes("registered")){
    return { message: "You’re already registered for this event.", type: "info" };
  }
  if(detail.includes("full")){
    return { message: "This event is full.", type: "error" };
  }
  return { message: "Unable to register for this event right now.", type: "error" };
}

async function fetchMyRegistrations(renderList=false){
  try {
    const res = await apiGetMyRegistrations();
    if(!res.ok){
      myRegistrations = new Map();
      myEvents = [];
      if(renderList){ renderMyEvents(); }
      return;
    }
    const data = await res.json();
    myRegistrations = new Map(data.map(r => [r.event.id, r.id]));
    myEvents = data.map(r => r.event);
    if(renderList){ renderMyEvents(); }
  } catch (err){
    console.error("Failed to load registrations", err);
    myRegistrations = new Map();
    myEvents = [];
    if(renderList){ renderMyEvents(); }
  }
}

function focusEvent(eventId){
  const row = document.getElementById(`event-row-${eventId}`);
  if(row){
    row.classList.add("highlight");
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => row.classList.remove("highlight"), 1600);
  } else {
    setStatus("events_status", "Event not in the current results. Run a search that includes it to jump there.", "error");
  }
}

function renderMyEvents(){
  const tbody = document.getElementById("my_events_tbody");
  tbody.innerHTML = "";
  if(myEvents.length === 0){
    tbody.innerHTML = '<tr><td colspan="4">No registrations yet for this user.</td></tr>';
    return;
  }

  myEvents
    .slice()
    .sort((a,b) => new Date(a.starts_at) - new Date(b.starts_at))
    .forEach(ev => {
      const tr = document.createElement("tr");
      tr.classList.add("clickable-row");
      tr.onclick = () => focusEvent(ev.id);
      tr.innerHTML = `<td>${ev.title}</td><td>${new Date(ev.starts_at).toLocaleString()}</td><td>${ev.location}</td><td>${ev.category}</td>`;
      tbody.appendChild(tr);
    });
}

async function createEvent(){
  const startsAt = requireDateTime("event_start", "events_status");
  if(!startsAt){ return; }
  const payload = {
    title: document.getElementById("event_title").value,
    starts_at: startsAt,
    location: document.getElementById("event_location").value,
    capacity: Number(document.getElementById("event_capacity").value),
    price_cents: Number(document.getElementById("event_price").value),
    category: document.getElementById("event_category").value,
    club_id: document.getElementById("event_club").value ? Number(document.getElementById("event_club").value) : null
  };
  const res = await apiCreateEvent(payload);
  const body = await readJson(res);
  if(res.ok){
    setStatus("events_status", "Event created successfully.", "success");
  } else {
    setStatus("events_status", `Create event failed: ${buildErrorMessage(res, body)}`, "error");
  }
  loadEvents();
}

function resetFilters(){
  document.getElementById("filter_start_date").value = "";
  document.getElementById("filter_start_hour").value = "";
  document.getElementById("filter_start_minute").value = "";
  document.getElementById("filter_start_ampm").value = "";
  document.getElementById("filter_end_date").value = "";
  document.getElementById("filter_end_hour").value = "";
  document.getElementById("filter_end_minute").value = "";
  document.getElementById("filter_end_ampm").value = "";
  document.getElementById("filter_category").value = "";
  document.getElementById("filter_title").value = "";
  document.getElementById("filter_location").value = "";
  document.getElementById("filter_sort").value = "date";
  document.getElementById("filter_free").checked = false;
  loadEvents();
}

function canManageEvent(event){
  const persona = currentPersona();
  if(persona.role === "admin"){ return true; }
  if(!event.club_id){ return false; }
  const membershipRole = clubRoles.get(event.club_id);
  return persona.role === "leader" && membershipRole === "leader";
}

async function loadEvents(skipRegistrationSync = false){
  clearStatus("events_status");
  const params = new URLSearchParams();
  const start = getSearchDateTime("filter_start");
  const end = getSearchDateTime("filter_end");
  const category = document.getElementById("filter_category").value;
  const title = document.getElementById("filter_title").value;
  const location = document.getElementById("filter_location").value;
  const sort = document.getElementById("filter_sort").value;
  if(start) params.set("start", start);
  if(end) params.set("end", end);
  if(category) params.set("category", category);
  if(title) params.set("title", title);
  if(location) params.set("location", location);
  if(document.getElementById("filter_free").checked) params.set("free_only", true);
  if(sort) params.set("sort", sort);

  if(!skipRegistrationSync){
    await fetchMyRegistrations(false);
  }
  const list = document.getElementById("events_list");
  list.innerHTML = "";

  let res;
  try {
    res = await apiGetEvents(params);
  } catch (err){
    setStatus("events_status", "Failed to load events. Please try again.", "error");
    list.innerHTML = '<div class="empty-state">Unable to reach the events service.</div>';
    return;
  }

  if(!res.ok){
    const body = await readJson(res);
    setStatus("events_status", `Failed to load events: ${buildErrorMessage(res, body)}`, "error");
    list.innerHTML = '<div class="empty-state">Unable to load events.</div>';
    return;
  }

  const data = await res.json();
  if(data.length === 0){
    list.innerHTML = '<div class="empty-state">No events found. Adjust your filters and try again.</div>';
    return;
  }

  data.forEach(ev => {
    const card = document.createElement("article");
    card.classList.add("event-card");
    card.id = `event-row-${ev.id}`;
    const price = formatPrice(ev.price_cents);
    const popularity = ev.registration_count ?? 0;
    const capacityText = ev.capacity ? `${popularity} registered out of ${ev.capacity} seats` : `${popularity} registered`;

    const header = document.createElement("div");
    header.className = "event-card__header";
    header.innerHTML = `
        <div>
          <p class="event-card__title">${ev.title}</p>
          <p class="event-card__datetime">${new Date(ev.starts_at).toLocaleString()}</p>
        </div>
        <div class="event-card__price">${price}</div>
      `;

    const meta = document.createElement("div");
    meta.className = "event-card__meta";
    meta.innerHTML = `
        <span class="pill">${ev.location}</span>
        <span class="pill pill-muted">${ev.category}</span>
      `;

    const stats = document.createElement("div");
    stats.className = "event-card__stats";
    stats.innerHTML = `
        <span class="seat-info">${capacityText}</span>
      `;

    const actions = document.createElement("div");
    actions.className = "event-card__actions";
    const isRegistered = myRegistrations.has(ev.id);
    const regBtn = document.createElement("button");
    regBtn.classList.add("btn-primary", "register-btn");
    regBtn.textContent = isRegistered ? "Unregister" : "Register";
    regBtn.onclick = () => isRegistered ? unregisterEvent(ev.id) : registerEvent(ev.id);
    const flagBtn = document.createElement("button");
    flagBtn.classList.add("btn-ghost");
    flagBtn.textContent = "Flag Content";
    flagBtn.onclick = () => flagEvent(ev.id);
    actions.appendChild(regBtn);
    actions.appendChild(flagBtn);
    if(canManageEvent(ev)){
      const deleteBtn = document.createElement("button");
      deleteBtn.classList.add("btn-secondary");
      deleteBtn.textContent = "Delete";
      deleteBtn.onclick = () => deleteEvent(ev.id);
      actions.appendChild(deleteBtn);
    }
    card.appendChild(header);
    card.appendChild(meta);
    card.appendChild(stats);
    card.appendChild(actions);
    list.appendChild(card);
  });
}

async function loadTrending(){
  const ul = document.getElementById("trending_list");
  ul.innerHTML = "";
  try {
    const res = await apiGetTrendingEvents();
    if(!res.ok){
      const body = await readJson(res);
      setStatus("events_status", `Failed to load trending: ${buildErrorMessage(res, body)}`, "error");
      ul.innerHTML = '<li>No trending events right now.</li>';
      return;
    }
    const data = await res.json();
    if(data.length === 0){
      ul.innerHTML = '<li>No trending events right now.</li>';
      return;
    }
    data.forEach(ev => {
      const li = document.createElement("li");
      li.textContent = `${ev.title} (${ev.registration_count} registrations)`;
      ul.appendChild(li);
    });
  } catch (err){
    setStatus("events_status", "Failed to load trending events.", "error");
    ul.innerHTML = '<li>No trending events right now.</li>';
  }
}

async function registerEvent(eventId){
  const res = await apiRegisterEvent(eventId);
  const body = await readJson(res);
  const { message, type } = buildRegistrationMessage(res, body);
  showStatus("events_status", message, type);
  await fetchMyRegistrations(true);
  await loadEvents(true);
}

async function unregisterEvent(eventId){
  const res = await apiUnregisterEvent(eventId);
  const message = res.ok ? "You are no longer registered for this event." : "We couldn’t update your registration right now.";
  const type = res.ok ? "success" : "error";
  showStatus("events_status", message, type);
  await fetchMyRegistrations(true);
  await loadEvents(true);
}

async function deleteEvent(eventId){
  if(!confirm("Delete this event?")){ return; }
  const res = await apiDeleteEvent(eventId);
  const detail = await readJson(res);
  const message = res.ok ? "Event deleted" : `Delete failed: ${buildErrorMessage(res, detail)}`;
  setStatus("events_status", message, res.ok ? "success" : "error");
  await fetchMyRegistrations(true);
  await loadEvents();
  if(loadedClubId){
    await loadClubDetail();
  }
}

async function loadMyEvents(){
  await fetchMyRegistrations(true);
}

async function flagEvent(id){
  const reason = prompt("Why are you flagging this event?");
  if(!reason){ return; }
  try {
    const res = await apiFlagItem({ item_type: "event", item_id: id, reason });
    const body = await readJson(res);
    if(res.ok){
      setStatus("events_status", "Flag submitted.", "success");
    } else {
      setStatus("events_status", `Flag failed: ${buildErrorMessage(res, body)}`, "error");
    }
  } catch (err){
    setStatus("events_status", "Flag failed.", "error");
  }
}

