let loadedClubId = null;
let myRegistrations = new Map();
let myEvents = [];
let clubMemberships = new Map();
let clubRoles = new Map();
let allClubs = [];
let myClubs = [];
let userProfile = null;
const sectionGroups = ["events", "clubs", "mystuff", "admin"];

function setUser(profile){
  userProfile = profile ? { ...profile } : null;
}

function resetUser(){
  userProfile = null;
}

function resetSharedState(){
  loadedClubId = null;
  myRegistrations = new Map();
  myEvents = [];
  clubMemberships = new Map();
  clubRoles = new Map();
  allClubs = [];
  myClubs = [];
}

function currentUser(){
  return userProfile;
}

function getSectionGroups(){
  return sectionGroups.slice();
}

