# **← Check the Document Tabs for your Quest Options\!**

# **🛡️ Quest: Reliability Engineering**

### ***Build a service that refuses to die easily.***

**The Mission:** In the real world, code breaks. Your job is to build a safety net so strong that even when things go wrong, the service keeps running.  
**Difficulty:** ⭐⭐ (Good starting point)

---

## **🥉 Tier 1: Bronze (The Shield)**

*Objective: Prove your code works before you ship it.*

### **⚔️ Main Objectives**

- [x] **Write Unit Tests:** Create a test suite using pytest. Test individual functions in isolation.  
- [x] **Automate Defense:** Set up GitHub Actions (or similar CI) to run tests on every commit.  
- [x] **Pulse Check:** Create a /health endpoint that returns 200 OK.

### **💡 Intel**

**Unit Tests?** Don't test the whole app. Just test that *Input A* leads to *Output B*.  
**Health Check?** Load balancers use this to know if your app is alive. If this fails, no traffic for you.

### **✅ Verification (Loot)**

- [x] CI Logs showing green/passing tests.  
- [x] A working GET /health endpoint.

---

## **🥈 Tier 2: Silver (The Fortress)**

*Objective: Stop bad code from ever reaching production.*

### **⚔️ Main Objectives**

- [x] **50% Coverage:** Use pytest-cov. Ensure half your code lines are hit by tests.  
- [x] **Integration Testing:** Write tests that hit the API (e.g., POST to /shorten  → Check DB).  
- [x] **The Gatekeeper:** Configure CI so deployment **fails** if tests fail.  
- [x] **Error Handling:** Document how your app handles 404s and 500s.

### **💡 Intel**

**Blocking Deploys:** This is the \#1 rule of SRE. Never ship broken code.  
**Integration vs Unit:** Unit tests check the engine; integration tests check if the car drives.

### **✅ Verification (Loot)**

- [x] Coverage report showing \>50%.  
- [ ] A screenshot of a blocked deploy due to a failed test.

---

## **🥇 Tier 3: Gold (The Immortal)**

*Objective: Break it on purpose. Watch it survive.*

### **⚔️ Main Objectives**

- [x] **70% Coverage:** High confidence in code stability.  
- [x] **Graceful Failure:** Send bad inputs. The app must return clean errors (JSON), not crash.  
- [ ] **Chaos Mode:** Kill the app process or container while it's running. Show it restarts automatically (e.g., Docker restart policy).  
- [x] **Failure Manual:** Document exactly what happens when things break (Failure Modes).

### **💡 Intel**

**Chaos Engineering:** Don't wait for a crash at 3 AM. Cause the crash at 2 PM and fix it.  
**Graceful:** A user should see "Service Unavailable," not a Python stack trace.

### **✅ Verification (Loot)**

- [ ] Live Demo: Kill the container→Watch it resurrect.  
- [x] Live Demo: Send garbage data→Get a polite error.  
- [x] Link to "Failure Mode" documentation.

---

**🧰 Recommended Loadout:** pytest, pytest-cov, GitHub Actions