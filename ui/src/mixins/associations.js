import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    assocTenantFilter: "",
    assocMode: "checkpoint",
    assocCheckpointSearchTerm: "",
    assocCheckpoints: [],
    assocCheckpointPage: 1,
    assocCheckpointSize: 5,
    assocCheckpointTotal: 0,
    assocCheckpointTotalPages: 1,
    expandedAssocCheckpoint: {},
    assocCheckpointMap: {},
    assocCheckpointSignalSearch: {},
    assocCheckpointCandidates: {},
    assocCheckpointCandidatePage: {},
    assocCheckpointCandidateSize: 5,
    assocCheckpointCandidateTotal: {},
    assocCheckpointCandidateTotalPages: {},
    expandedAssocCheckpointCandidate: {},
    assocSignalSearchTerm: "",
    assocSignals: [],
    assocSignalPage: 1,
    assocSignalSize: 5,
    assocSignalTotal: 0,
    assocSignalTotalPages: 1,
    expandedAssocSignal: {},
    assocSignalMap: {},
    assocSignalCheckpointSearch: {},
    assocSignalCandidates: {},
    assocSignalCandidatePage: {},
    assocSignalCandidateSize: 5,
    assocSignalCandidateTotal: {},
    assocSignalCandidateTotalPages: {},
    expandedAssocSignalCandidate: {}
    };
  },
  methods: {
    searchAssocCheckpoints(page) {
      this.assocCheckpointPage = page;
      const q = encodeURIComponent(this.assocCheckpointSearchTerm.trim());
      if (!q) {
        this.loadAllAssocCheckpoints(page);
        return;
      }
      const url = `/ui/search_checkpoints?q=${q}&page=${page}&size=${this.assocCheckpointSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.assocCheckpoints = filtered;
          this.assocCheckpointTotal = data.total;
          this.assocCheckpointTotalPages = Math.ceil(data.total / this.assocCheckpointSize);
          this.assocCheckpoints.forEach(cp => {
            this.expandedAssocCheckpoint[cp.id] = false;
            this.loadAssocCheckpointMap(cp.id);
          });
        })
        .catch(err => console.error("Error searching assoc checkpoints:", err));
    },

    loadAllAssocCheckpoints(page) {
      this.assocCheckpointPage = page;
      let url = `/ui/checkpoints?page=${page}&size=${this.assocCheckpointSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.assocCheckpoints = filtered;
          this.assocCheckpointTotal = data.total;
          this.assocCheckpointTotalPages = Math.ceil(data.total / this.assocCheckpointSize);
          this.assocCheckpoints.forEach(cp => {
            this.expandedAssocCheckpoint[cp.id] = false;
            this.loadAssocCheckpointMap(cp.id);
          });
        })
        .catch(err => console.error("Error loading all assoc checkpoints:", err));
    },

    toggleExpandAssocCheckpoint(cpId) {
      this.expandedAssocCheckpoint[cpId] = !this.expandedAssocCheckpoint[cpId];
    },

    loadAssocCheckpointMap(cpId) {
      api.request(`/ui/signals?checkpoint_id=${cpId}&page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          if (!this.assocCheckpointMap[cpId]) {
            this.assocCheckpointMap[cpId] = { signals: [] };
          }
          this.assocCheckpointMap[cpId].signals = data.items || [];
        })
        .catch(err => console.error("Error loading assoc checkpoint map:", err));
    },

    prevAssocCheckpointPage() {
      if (this.assocCheckpointPage > 1) {
        if (!this.assocCheckpointSearchTerm.trim()) {
          this.loadAllAssocCheckpoints(this.assocCheckpointPage - 1);
        } else {
          this.searchAssocCheckpoints(this.assocCheckpointPage - 1);
        }
      }
    },

    nextAssocCheckpointPage() {
      if (this.assocCheckpointPage < this.assocCheckpointTotalPages) {
        if (!this.assocCheckpointSearchTerm.trim()) {
          this.loadAllAssocCheckpoints(this.assocCheckpointPage + 1);
        } else {
          this.searchAssocCheckpoints(this.assocCheckpointPage + 1);
        }
      }
    },

    searchSignalsToAssociate(cpId, page) {
      this.assocCheckpointCandidatePage[cpId] = page;
      const q = this.assocCheckpointSignalSearch[cpId] || "";
      if (!q.trim()) {
        this.loadAllSignalsToAssociate(cpId, page);
        return;
      }
      let url = `/ui/search_signals?q=${encodeURIComponent(q)}&page=${page}&size=${this.assocCheckpointCandidateSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.assocCheckpointCandidates[cpId] = filtered;
          this.assocCheckpointCandidateTotal[cpId] = data.total;
          this.assocCheckpointCandidateTotalPages[cpId] = Math.ceil(data.total / this.assocCheckpointCandidateSize);
          if (!this.expandedAssocCheckpointCandidate[cpId]) {
            this.expandedAssocCheckpointCandidate[cpId] = {};
          }
          filtered.forEach(s => {
            this.expandedAssocCheckpointCandidate[cpId][s.id] = false;
          });
        })
        .catch(err => console.error("Error searching signals to associate:", err));
    },

    loadAllSignalsToAssociate(cpId, page) {
      this.assocCheckpointCandidatePage[cpId] = page;
      let url = `/ui/signals?page=${page}&size=${this.assocCheckpointCandidateSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.assocCheckpointCandidates[cpId] = filtered;
          this.assocCheckpointCandidateTotal[cpId] = data.total;
          this.assocCheckpointCandidateTotalPages[cpId] = Math.ceil(data.total / this.assocCheckpointCandidateSize);
          if (!this.expandedAssocCheckpointCandidate[cpId]) {
            this.expandedAssocCheckpointCandidate[cpId] = {};
          }
          filtered.forEach(s => {
            this.expandedAssocCheckpointCandidate[cpId][s.id] = false;
          });
        })
        .catch(err => console.error("Error loading signals to associate:", err));
    },

    toggleExpandAssocCheckpointCandidate(cpId, sid) {
      if (!this.expandedAssocCheckpointCandidate[cpId]) {
        this.expandedAssocCheckpointCandidate[cpId] = {};
      }
      this.expandedAssocCheckpointCandidate[cpId][sid] = !this.expandedAssocCheckpointCandidate[cpId][sid];
    },

    associateSignalToCheckpoint2(cpId, sigId) {
      this.associateSignalToCheckpoint(cpId, sigId);
    },

    prevAssocCheckpointCandidatePage(cpId) {
      if (this.assocCheckpointCandidatePage[cpId] > 1) {
        this.assocCheckpointCandidatePage[cpId]--;
        this.searchSignalsToAssociate(cpId, this.assocCheckpointCandidatePage[cpId]);
      }
    },

    nextAssocCheckpointCandidatePage(cpId) {
      if (this.assocCheckpointCandidatePage[cpId] < this.assocCheckpointCandidateTotalPages[cpId]) {
        this.assocCheckpointCandidatePage[cpId]++;
        this.searchSignalsToAssociate(cpId, this.assocCheckpointCandidatePage[cpId]);
      }
    },

    // By Signal,

    searchAssocSignals(page) {
      this.assocSignalPage = page;
      const q = encodeURIComponent(this.assocSignalSearchTerm.trim());
      if (!q) {
        this.loadAllAssocSignals(page);
        return;
      }
      let url = `/ui/search_signals?q=${q}&page=${page}&size=${this.assocSignalSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.assocSignals = filtered;
          this.assocSignalTotal = data.total;
          this.assocSignalTotalPages = Math.ceil(data.total / this.assocSignalSize);
          this.assocSignals.forEach(s => {
            this.expandedAssocSignal[s.id] = false;
            this.loadAssocSignalMap(s.id);
          });
        })
        .catch(err => console.error("Error searching assoc signals:", err));
    },

    loadAllAssocSignals(page) {
      this.assocSignalPage = page;
      let url = `/ui/signals?page=${page}&size=${this.assocSignalSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.assocSignals = filtered;
          this.assocSignalTotal = data.total;
          this.assocSignalTotalPages = Math.ceil(data.total / this.assocSignalSize);
          this.assocSignals.forEach(s => {
            this.expandedAssocSignal[s.id] = false;
            this.loadAssocSignalMap(s.id);
          });
        })
        .catch(err => console.error("Error loading all assoc signals:", err));
    },

    toggleExpandAssocSignal(sid) {
      this.expandedAssocSignal[sid] = !this.expandedAssocSignal[sid];
    },

    loadAssocSignalMap(sid) {
      api.request(`/ui/checkpoints?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const allCps = data.items;
          return api.request(`/ui/checkpoint_signals?page=1&size=9999`).then(r => r.json()).then(assocData => {
            const relevant = assocData.items.filter(a => a.signal_id === sid);
            const cpIds = relevant.map(r => r.checkpoint_id);
            const associated = allCps.filter(cp => cpIds.includes(cp.id));
            if (!this.assocSignalMap[sid]) {
              this.assocSignalMap[sid] = { checkpoints: [] };
            }
            this.assocSignalMap[sid].checkpoints = associated;
          });
        })
        .catch(err => console.error("Error loadAssocSignalMap:", err));
    },

    prevAssocSignalPage() {
      if (this.assocSignalPage > 1) {
        if (!this.assocSignalSearchTerm.trim()) {
          this.loadAllAssocSignals(this.assocSignalPage - 1);
        } else {
          this.searchAssocSignals(this.assocSignalPage - 1);
        }
      }
    },

    nextAssocSignalPage() {
      if (this.assocSignalPage < this.assocSignalTotalPages) {
        if (!this.assocSignalSearchTerm.trim()) {
          this.loadAllAssocSignals(this.assocSignalPage + 1);
        } else {
          this.searchAssocSignals(this.assocSignalPage + 1);
        }
      }
    },

    searchCheckpointsToAssociate(sid, page) {
      this.assocSignalCandidatePage[sid] = page;
      const q = this.assocSignalCheckpointSearch[sid] || "";
      if (!q.trim()) {
        this.loadAllCheckpointsToAssociate(sid, page);
        return;
      }
      const url = `/ui/search_checkpoints?q=${encodeURIComponent(q)}&page=${page}&size=${this.assocSignalCandidateSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.assocSignalCandidates[sid] = filtered;
          this.assocSignalCandidateTotal[sid] = data.total;
          this.assocSignalCandidateTotalPages[sid] = Math.ceil(data.total / this.assocSignalCandidateSize);
          if (!this.expandedAssocSignalCandidate[sid]) {
            this.expandedAssocSignalCandidate[sid] = {};
          }
          filtered.forEach(cp => {
            this.expandedAssocSignalCandidate[sid][cp.id] = false;
          });
        })
        .catch(err => console.error("Error searching checkpoints to associate with signal:", err));
    },

    loadAllCheckpointsToAssociate(sid, page) {
      this.assocSignalCandidatePage[sid] = page;
      const url = `/ui/checkpoints?page=${page}&size=${this.assocSignalCandidateSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.assocSignalCandidates[sid] = filtered;
          this.assocSignalCandidateTotal[sid] = data.total;
          this.assocSignalCandidateTotalPages[sid] = Math.ceil(data.total / this.assocSignalCandidateSize);
          if (!this.expandedAssocSignalCandidate[sid]) {
            this.expandedAssocSignalCandidate[sid] = {};
          }
          filtered.forEach(cp => {
            this.expandedAssocSignalCandidate[sid][cp.id] = false;
          });
        })
        .catch(err => console.error("Error loading all checkpoints to associate with signal:", err));
    },

    toggleExpandAssocSignalCandidate(sid, cpId) {
      if (!this.expandedAssocSignalCandidate[sid]) {
        this.expandedAssocSignalCandidate[sid] = {};
      }
      this.expandedAssocSignalCandidate[sid][cpId] = !this.expandedAssocSignalCandidate[sid][cpId];
    },

    associateCheckpointToSignal2(sid, cpId) {
      this.associateCheckpointToSignal(sid, cpId);
    },

    prevAssocSignalCandidatePage(sid) {
      if (this.assocSignalCandidatePage[sid] > 1) {
        this.assocSignalCandidatePage[sid]--;
        this.searchCheckpointsToAssociate(sid, this.assocSignalCandidatePage[sid]);
      }
    },

    nextAssocSignalCandidatePage(sid) {
      if (this.assocSignalCandidatePage[sid] < this.assocSignalCandidateTotalPages[sid]) {
        this.assocSignalCandidatePage[sid]++;
        this.searchCheckpointsToAssociate(sid, this.assocSignalCandidatePage[sid]);
      }
    },

    //---------------------------------------
    // SEARCH
    //---------------------------------------
  }
};
