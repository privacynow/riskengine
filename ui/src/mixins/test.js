import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    testDecTenantFilter: "",
    testDecCheckpointSearchTerm: "",
    testDecCheckpoints: [],
    testDecCheckpointPage: 1,
    testDecCheckpointSize: 5,
    testDecCheckpointTotal: 0,
    testDecCheckpointTotalPages: 1,
    expandedTestDecCheckpoints: {},
    testDecApplicantIds: {},
    testDecCorrelationIds: {},
    testDecAssocSignals: {},
    expandedTestDecSignals: {},
    testDecParams: {},
    testDecResponses: {}
    };
  },
  methods: {
    searchTestDecCheckpoints(page) {
      this.testDecCheckpointPage = page;
      const q = encodeURIComponent(this.testDecCheckpointSearchTerm.trim());
      if (!q && !this.testDecTenantFilter) {
        this.loadAllTestDecCheckpoints(page);
        return;
      }
      if (!q) {
        this.loadAllTestDecCheckpoints(page);
        return;
      }
      const url = `/ui/search_checkpoints?q=${q}&page=${page}&size=${this.testDecCheckpointSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.testDecTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.testDecTenantFilter);
          }
          this.testDecCheckpoints = filtered;
          this.testDecCheckpointTotal = data.total;
          this.testDecCheckpointTotalPages = Math.ceil(data.total / this.testDecCheckpointSize);
          this.testDecCheckpoints.forEach(cp => {
            this.expandedTestDecCheckpoints[cp.id] = false;
          });
        })
        .catch(err => console.error("Error searching test dec checkpoints:", err));
    },

    loadAllTestDecCheckpoints(page) {
      this.testDecCheckpointPage = page;
      let url = `/ui/checkpoints?page=${page}&size=${this.testDecCheckpointSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.testDecTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.testDecTenantFilter);
          }
          this.testDecCheckpoints = filtered;
          this.testDecCheckpointTotal = data.total;
          this.testDecCheckpointTotalPages = Math.ceil(data.total / this.testDecCheckpointSize);
          this.testDecCheckpoints.forEach(cp => {
            this.expandedTestDecCheckpoints[cp.id] = false;
          });
        })
        .catch(err => console.error("Error loading all test dec checkpoints:", err));
    },

    toggleExpandTestDecCheckpoint(cpId) {
      this.expandedTestDecCheckpoints[cpId] = !this.expandedTestDecCheckpoints[cpId];
      if (this.expandedTestDecCheckpoints[cpId]) {
        this.loadTestDecCheckpointSignals(cpId);
      }
    },

    loadTestDecCheckpointSignals(cpId) {
      // Get signals for this checkpoint
      const url = `/ui/signals?checkpoint_id=${cpId}&page=1&size=9999`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          const signals = data.items || [];
          this.testDecAssocSignals[cpId] = signals;
          if (!this.expandedTestDecSignals[cpId]) {
            this.expandedTestDecSignals[cpId] = {};
          }
          signals.forEach(sig => {
            this.expandedTestDecSignals[cpId][sig.id] = false;
          });
          if (!this.testDecParams[cpId]) {
            this.testDecParams[cpId] = {};
          }
          signals.forEach(sig => {
            if (!this.testDecParams[cpId][sig.id]) {
              this.testDecParams[cpId][sig.id] = {};
              sig.param_placeholders.forEach(ph => {
                this.testDecParams[cpId][sig.id][ph] = "";
              });
            }
          });
        })
        .catch(err => console.error("Error loading checkpoint signals for test:", err));
    },

    toggleExpandTestDecSignal(cpId, sigId) {
      if (!this.expandedTestDecSignals[cpId]) {
        this.expandedTestDecSignals[cpId] = {};
      }
      this.expandedTestDecSignals[cpId][sigId] = !this.expandedTestDecSignals[cpId][sigId];
    },

    prevTestDecCheckpointPage() {
      if (this.testDecCheckpointPage > 1) {
        this.testDecCheckpointPage--;
        this.searchTestDecCheckpoints(this.testDecCheckpointPage);
      }
    },

    nextTestDecCheckpointPage() {
      if (this.testDecCheckpointPage < this.testDecCheckpointTotalPages) {
        this.testDecCheckpointPage++;
        this.searchTestDecCheckpoints(this.testDecCheckpointPage);
      }
    },

    invokeTestDecision(cpId) {
      const cp = this.testDecCheckpoints.find(c => c.id === cpId);
      if (!cp) {
        notify( { message: "Checkpoint not found in test list.", isError: true });
        return;
      }
      const applicantId = this.testDecApplicantIds[cpId] || undefined;
      const correlationId = this.testDecCorrelationIds[cpId] || undefined;

      // gather placeholders from the user's input
      const paramMap = {};
      const signalParamData = this.testDecParams[cpId] || {};
      Object.keys(signalParamData).forEach(sigId => {
        const placeholdersObj = signalParamData[sigId];
        Object.keys(placeholdersObj).forEach(ph => {
          paramMap[ph] = placeholdersObj[ph];
        });
      });

      const payload = {
        tenant_id: cp.tenant_id,
        checkpoint_name: cp.name,
        applicant_id: applicantId,
        correlation_id: correlationId,
        parameters: paramMap
      };

      api.request("/ui/test_decisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(async r => {
          if (!r.ok) {
            const txt = await r.text();
            throw new Error(`Decision error: ${txt}`);
          }
          return r.json();
        })
        .then(resp => {
          this.testDecResponses[cpId] = resp;
        })
        .catch(err => {
          console.error("Error invoking decision:", err);
          this.testDecResponses[cpId] = { error: err.message };
        });
    },

    //---------------------------------------
    // Helpers for DSL placeholders in UI
    //---------------------------------------
  }
};
