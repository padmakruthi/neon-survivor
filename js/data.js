// ═══════════════════════════════════════════
// data.js — Static reference data
// Used only for drawing charts in the dashboard
//
// NOTE: Messages and Predictions are now handled
// by the real backend (app.js makes API calls)
// ═══════════════════════════════════════════

// ── BATCH DATA ──
// Used for the Dissolution Rate chart on dashboard
// These are the real 60 batch values from the Excel file
const BATCH_DATA = [
  {id:"T001",gran:15,binder:8.5,dryTemp:60,dryTime:25,compForce:12.5,speed:150,lubricant:1.0,moisture:2.1,hardness:95,friability:0.65,dissolution:89.3,uniformity:98.7},
  {id:"T002",gran:12,binder:7.0,dryTemp:65,dryTime:20,compForce:15.0,speed:120,lubricant:0.8,moisture:2.8,hardness:110,friability:0.45,dissolution:87.9,uniformity:101.2},
  {id:"T003",gran:18,binder:9.2,dryTemp:55,dryTime:30,compForce:10.8,speed:180,lubricant:1.2,moisture:1.9,hardness:85,friability:0.78,dissolution:91.5,uniformity:97.3},
  {id:"T004",gran:20,binder:10.0,dryTemp:58,dryTime:35,compForce:8.5,speed:200,lubricant:1.5,moisture:1.5,hardness:72,friability:0.95,dissolution:93.8,uniformity:95.9},
  {id:"T005",gran:10,binder:6.5,dryTemp:70,dryTime:18,compForce:16.2,speed:100,lubricant:0.6,moisture:3.2,hardness:125,friability:0.38,dissolution:85.1,uniformity:103.5},
  {id:"T006",gran:16,binder:8.8,dryTemp:62,dryTime:28,compForce:11.8,speed:160,lubricant:1.1,moisture:2.3,hardness:92,friability:0.72,dissolution:88.7,uniformity:99.1},
  {id:"T007",gran:14,binder:7.5,dryTemp:67,dryTime:22,compForce:13.5,speed:140,lubricant:0.9,moisture:2.6,hardness:102,friability:0.58,dissolution:86.4,uniformity:100.8},
  {id:"T008",gran:22,binder:11.0,dryTemp:52,dryTime:38,compForce:7.2,speed:220,lubricant:1.8,moisture:1.2,hardness:65,friability:1.15,dissolution:95.7,uniformity:94.2},
  {id:"T009",gran:13,binder:7.8,dryTemp:63,dryTime:24,compForce:14.2,speed:130,lubricant:0.7,moisture:2.4,hardness:108,friability:0.52,dissolution:88.9,uniformity:102.1},
  {id:"T010",gran:17,binder:9.5,dryTemp:59,dryTime:32,compForce:9.8,speed:170,lubricant:1.4,moisture:1.8,hardness:78,friability:0.88,dissolution:92.3,uniformity:96.8},
  {id:"T011",gran:19,binder:9.8,dryTemp:57,dryTime:33,compForce:9.2,speed:185,lubricant:1.3,moisture:1.7,hardness:75,friability:0.91,dissolution:92.8,uniformity:96.5},
  {id:"T012",gran:11,binder:6.8,dryTemp:68,dryTime:19,compForce:15.8,speed:110,lubricant:0.7,moisture:3.0,hardness:120,friability:0.42,dissolution:86.1,uniformity:102.8},
  {id:"T013",gran:21,binder:10.5,dryTemp:54,dryTime:36,compForce:7.5,speed:215,lubricant:1.6,moisture:1.4,hardness:70,friability:1.02,dissolution:96.0,uniformity:94.5},
  {id:"T014",gran:23,binder:11.5,dryTemp:50,dryTime:40,compForce:6.5,speed:240,lubricant:2.0,moisture:1.0,hardness:58,friability:1.28,dissolution:97.2,uniformity:93.1},
  {id:"T015",gran:15,binder:8.2,dryTemp:61,dryTime:26,compForce:12.0,speed:155,lubricant:1.05,moisture:2.2,hardness:93,friability:0.67,dissolution:89.0,uniformity:98.5},
  {id:"T018",gran:21,binder:10.8,dryTemp:53,dryTime:37,compForce:7.8,speed:210,lubricant:1.7,moisture:1.3,hardness:68,friability:1.08,dissolution:96.4,uniformity:94.8},
  {id:"T025",gran:24,binder:12.0,dryTemp:48,dryTime:42,compForce:6.0,speed:250,lubricant:2.2,moisture:0.8,hardness:52,friability:1.42,dissolution:98.6,uniformity:92.4},
  {id:"T036",gran:25,binder:12.5,dryTemp:46,dryTime:44,compForce:5.5,speed:260,lubricant:2.4,moisture:0.6,hardness:48,friability:1.58,dissolution:99.1,uniformity:91.8},
  {id:"T045",gran:26,binder:13.0,dryTemp:44,dryTime:46,compForce:5.0,speed:270,lubricant:2.6,moisture:0.4,hardness:44,friability:1.74,dissolution:99.8,uniformity:90.5},
  {id:"T056",gran:27,binder:13.5,dryTemp:42,dryTime:48,compForce:4.5,speed:280,lubricant:2.8,moisture:0.2,hardness:40,friability:1.92,dissolution:99.9,uniformity:89.8},
];

// ── QUALITY STANDARDS ──
// Used for checking pass/fail on frontend display
const STANDARDS = {
  dissolution: { min: 85,  max: 100, label: "≥85%" },
  hardness:    { min: 80,  max: 130, label: "80–130 N" },
  friability:  { min: 0,   max: 1.0, label: "≤1.0%" },
  uniformity:  { min: 95,  max: 105, label: "95–105%" },
  moisture:    { min: 0,   max: 3.0, label: "≤3.0%" },
};