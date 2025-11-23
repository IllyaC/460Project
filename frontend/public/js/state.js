let loadedClubId = null;
let myRegistrations = new Map();
let myEvents = [];
let clubMemberships = new Map();
let clubRoles = new Map();
let allClubs = [];
let myClubs = [];
let personaName = "";
let personaEmail = "";
let personaRole = "";
const sectionGroups = ["events", "clubs", "mystuff", "admin"];

function setPersona(name, email, role){
  personaName = name;
  personaEmail = email;
  personaRole = role;
}

function resetPersona(){
  personaName = "";
  personaEmail = "";
  personaRole = "";
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

function currentPersona(){
  return {
    email: personaEmail,
    role: personaRole
  };
}

function getSectionGroups(){
  return sectionGroups.slice();
}

