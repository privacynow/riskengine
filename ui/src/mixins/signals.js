import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    signalsActiveFilter: "all",
    signalSearchTerm: "",
    showSignalCreateForm: false,
    signals: [],
    signalPage: 1,
    signalSize: 5,
    signalTotal: 0,
    signalTotalPages: 1,
    expandedSignals: {},
    signalEdits: {},
    newSignalName: "",
    newSignalDescription: "",
    newSignalType: "variable",
    newSignalMethodOfCall: "",
    newSignalExpressionBody: "",
    newSignalCost: 0,
    newSignalCacheExpiration: 0,
    newSignalTimeout: 30,
    newSignalCanRunParallel: false,
    newSignalOrderEval: 1,
    newSignalHttpMethod: "GET",
    newSignalBearerToken: "",
    newSignalUrlParams: "",
    newSignalBodyTemplate: "",
    newSignalHeadersTemplate: "",
    newSignalAllowCaching: false,
    newSignalGlobalReuse: false,
    newSignalFunctionParams: "",
    signalCheckpointSearch: {},
    signalCheckpointCandidates: {},
    signalCheckpointCandidatePage: {},
    signalCheckpointCandidateSize: 5,
    signalCheckpointCandidateTotal: {},
    signalCheckpointCandidateTotalPages: {},
    expandedSignalCandidate: {},
    newSignalData: {
      name: '',
      description: '',
      type: 'variable',
      method_of_call: '',
      expression_body: '',
      cost: 0,
      cache_expiration_seconds: 0,
      timeout_seconds: 30,
      can_run_in_parallel: false,
      order_of_evaluation: 1,
      http_method: 'GET',
      bearer_token: '',
      request_url_params_template: '',
      request_body_template: '',
      request_headers_template: '',
      allow_caching: false,
      global_reuse: false,
      function_params_template: '',
      makeCurrentVersion: false
    }
    };
  },
  methods: {
    toggleSignalCreateForm() {
      this.showSignalCreateForm = !this.showSignalCreateForm;
    },

    loadAllSignals(page, updateSignalId = null) {
      const pageNum = parseInt(page) || 1;
      this.signalPage = pageNum;
      
      const params = new URLSearchParams({
        page: pageNum,
        size: this.signalSize
      });
      
      if (this.currentGlobalTenant) {
        params.append('tenant_id', this.currentGlobalTenant.id);
      }
      if (this.signalsActiveFilter === 'active') {
        params.append('active_only', 'true');
      }
      
      api.request(`/ui/signals?${params.toString()}`)
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => {
              throw new Error(`Failed to fetch signals: ${text}`);
            });
          }
          return response.json();
        })
        .then(data => {
          if (updateSignalId) {
            // Only update the specific signal's data
            const updatedSignal = data.items.find(s => s.id === updateSignalId);
            if (updatedSignal) {
              const index = this.signals.findIndex(s => s.id === updateSignalId);
              if (index !== -1) {
                this.signals[index] = updatedSignal;
              }
            }
          } else {
            // Full reload
          this.signals = data.items;
          this.signalTotal = data.total;
          this.signalTotalPages = Math.ceil(data.total / this.signalSize);
          this.signals.forEach(s => {
            this.expandedSignals[s.id] = false;
            this.signalEdits[s.id] = {
              name: s.name,
              description: s.description,
              method_of_call: s.method_of_call,
              cost: s.cost,
              bearer_token_input: "",
              associatedCheckpoints: []
            };
            this.loadSignalAssociations(s.id);
            });
          }
        })
        .catch(err => {
          console.error("Error loading signals:", err);
          if (!updateSignalId) {
            this.signals = [];
            this.signalTotal = 0;
            this.signalTotalPages = 1;
          }
        });
    },

    searchSignals(query, page = 1) {
      const q = encodeURIComponent(query.trim());
      if (!q && !this.currentGlobalTenant) {
        this.loadAllSignals(page);
        return;
      }
      if (!q) {
        this.loadAllSignals(page);
        return;
      }
      let url = `/ui/search_signals?q=${q}&page=${page}&size=${this.signalSize}`;
      if (this.currentGlobalTenant) {
        url += `&tenant_id=${this.currentGlobalTenant.id}`;
      }
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      api.request(url)
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => {
              throw new Error(`Failed to fetch signals: ${text}`);
            });
          }
          return response.json();
        })
        .then(data => {
          this.signals = data.items;
          this.signalTotal = data.total;
          this.signalTotalPages = Math.ceil(data.total / this.signalSize);
          this.signalPage = page;
          this.signals.forEach(s => {
            this.expandedSignals[s.id] = false;
            this.signalEdits[s.id] = {
              name: s.name,
              description: s.description,
              method_of_call: s.method_of_call,
              cost: s.cost,
              bearer_token_input: "",
              associatedCheckpoints: []
            };
            this.loadSignalAssociations(s.id);
          });
        })
        .catch(err => {
          console.error("Error searching signals:", err);
          this.signals = [];
          this.signalTotal = 0;
          this.signalTotalPages = 1;
          this.signalPage = 1;
        });
    },

    nextSignalPage() {
      if (this.signalPage < this.signalTotalPages) {
        this.loadAllSignals(this.signalPage + 1);
      }
    },

    prevSignalPage() {
      if (this.signalPage > 1) {
        this.loadAllSignals(this.signalPage - 1);
      }
    },

    loadSignalAssociations(sid) {
      api.request(`/ui/checkpoints?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const allCps = data.items;
          return api.request(`/ui/checkpoint_signals?page=1&size=9999`).then(r => r.json()).then(assocData => {
            const relevant = assocData.items.filter(a => a.signal_id === sid);
            const cpIds = relevant.map(r => r.checkpoint_id);
            const associatedCps = allCps.filter(cp => cpIds.includes(cp.id));
            this.signalEdits[sid].associatedCheckpoints = associatedCps;
          });
        })
        .catch(err => console.error("Error loading signal associations:", err));
    },

    removeCheckpointAssociation(sigId, cpId) {
      api.request(`/ui/checkpoint_signals?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const assoc = data.items.find(a => a.signal_id === sigId && a.checkpoint_id === cpId);
          if (!assoc) {
            notify( { message: "Association not found.", isError: true });
            return;
          }
          return api.request(`/ui/checkpoint_signals/${assoc.id}`, { method: "DELETE" });
        })
        .then(resp => {
          if (!resp) return;
          if (!resp.ok) {
            throw new Error("Failed to remove association.");
          }
          this.loadSignalAssociations(sigId);
        })
        .catch(err => console.error("Error removing checkpoint association from signal:", err));
    },

    createSignal() {
      if (!this.currentGlobalTenant) {
        notify( { message: "Please select a tenant first.", isError: true });
        return;
      }
      
      const payload = {
        tenant_id: this.currentGlobalTenant.id,
        ...this.newSignalData
      };

      api.request("/ui/signals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(r => {
          if (!r.ok) {
            return r.text().then(text => { throw new Error(text); });
          }
          return r.json();
        })
        .then(created => {
          // Reset form data
          this.newSignalData = {
            name: '',
            description: '',
            type: 'variable',
            method_of_call: '',
            expression_body: '',
            cost: 0,
            cache_expiration_seconds: 0,
            timeout_seconds: 30,
            can_run_in_parallel: false,
            order_of_evaluation: 1,
            http_method: 'GET',
            bearer_token: '',
            request_url_params_template: '',
            request_body_template: '',
            request_headers_template: '',
            allow_caching: false,
            global_reuse: false,
            function_params_template: '',
            makeCurrentVersion: false
          };
          this.showSignalCreateForm = false;
          this.loadAllSignals(this.signalPage);
        })
        .catch(err => {
          console.error("Error creating signal:", err);
          notify( { message: 'Error creating signal: ' + err.message, isError: true });
        });
    },

    toggleExpandSignal(sid) {
      this.expandedSignals[sid] = !this.expandedSignals[sid];
    },

    saveSignal(signalId) {
      if (!this.signalEdits[signalId]) return;
      
      const signal = this.signals.find(s => s.id === signalId);
      if (!signal) return;

          const payload = {
        tenant_id: signal.tenant_id,
        name: signal.name,
        type: signal.type,
        description: signal.description || "",
        method_of_call: this.signalEdits[signalId].method_of_call || signal.method_of_call,
        expression_body: signal.expression_body || "",
        cost: this.signalEdits[signalId].cost || signal.cost,
        cache_expiration_seconds: signal.cache_expiration_seconds || 0,
        timeout_seconds: signal.timeout_seconds || 30,
        can_run_in_parallel: signal.can_run_in_parallel || false,
        order_of_evaluation: signal.order_of_evaluation || 1,
        http_method: signal.http_method || "GET",
        request_url_params_template: signal.request_url_params_template || "",
        request_body_template: signal.request_body_template || "",
        request_headers_template: signal.request_headers_template || "",
        allow_caching: signal.allow_caching || false,
        global_reuse: signal.global_reuse || false,
        function_params_template: signal.function_params_template || ""
      };
      const tokenInput = (this.signalEdits[signalId].bearer_token_input || "").trim();
      if (tokenInput) {
        payload.bearer_token = tokenInput;
      }

      api.request(`/ui/signals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
      })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => { throw new Error(text); });
        }
        return response.json();
      })
      .then(data => {
        this.expandedSignals[signalId] = false;
          this.loadAllSignals(this.signalPage);
        })
      .catch(error => {
        console.error('Error saving signal:', error);
        notify( { message: 'Error saving signal: ' + error.message, isError: true });
      });
    },

    fetchCheckpointsForSignalEdit(sid, page) {
      this.signalCheckpointCandidatePage[sid] = page;
      const q = encodeURIComponent(this.signalCheckpointSearch[sid].trim());
      if (!q) {
        this.loadAllCheckpointsForSignalEdit(sid, page);
        return;
      }
      const url = `/ui/search_checkpoints?q=${q}&page=${page}&size=${this.signalCheckpointCandidateSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          this.signalCheckpointCandidates[sid] = data.items || [];
          this.signalCheckpointCandidateTotal[sid] = data.total;
          this.signalCheckpointCandidateTotalPages[sid] = Math.ceil(data.total / this.signalCheckpointCandidateSize);
          this.signalCheckpointCandidates[sid].forEach(cp => {
            if (!this.expandedSignalCandidate[sid]) {
              this.expandedSignalCandidate[sid] = {};
            }
            this.expandedSignalCandidate[sid][cp.id] = false;
          });
        })
        .catch(err => console.error("Error searching checkpoints for signal edit:", err));
    },

    loadAllCheckpointsForSignalEdit(sid, page) {
      this.signalCheckpointCandidatePage[sid] = page;
      const url = `/ui/checkpoints?page=${page}&size=${this.signalCheckpointCandidateSize}`;
      api.request(url)
        .then(r => r.json())
        .then(data => {
          this.signalCheckpointCandidates[sid] = data.items || [];
          this.signalCheckpointCandidateTotal[sid] = data.total;
          this.signalCheckpointCandidateTotalPages[sid] = Math.ceil(data.total / this.signalCheckpointCandidateSize);
          this.signalCheckpointCandidates[sid].forEach(cp => {
            if (!this.expandedSignalCandidate[sid]) {
              this.expandedSignalCandidate[sid] = {};
            }
            this.expandedSignalCandidate[sid][cp.id] = false;
          });
        })
        .catch(err => console.error("Error loading all checkpoints for signal edit:", err));
    },

    toggleExpandSignalCandidate(sid, cpId) {
      if (!this.expandedSignalCandidate[sid]) {
        this.expandedSignalCandidate[sid] = {};
      }
      this.expandedSignalCandidate[sid][cpId] = !this.expandedSignalCandidate[sid][cpId];
    },

    nextSignalCheckpointCandidatePage(sid) {
      if (this.signalCheckpointCandidatePage[sid] < this.signalCheckpointCandidateTotalPages[sid]) {
        this.fetchCheckpointsForSignalEdit(sid, this.signalCheckpointCandidatePage[sid] + 1);
      }
    },

    prevSignalCheckpointCandidatePage(sid) {
      if (this.signalCheckpointCandidatePage[sid] > 1) {
        this.fetchCheckpointsForSignalEdit(sid, this.signalCheckpointCandidatePage[sid] - 1);
      }
    },

    associateCheckpointToSignal(sid, cpId) {
      const payload = { checkpoint_id: cpId, signal_id: sid };
      api.request("/ui/checkpoint_signals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(r => {
          if (!r.ok) {
            return r.text().then(txt => { throw new Error(txt); });
          }
          return r.json();
        })
        .then(created => {
          this.loadSignalAssociations(sid);
        })
        .catch(err => console.error("Error associating checkpoint to signal:", err));
    },

    //---------------------------------------
    // ASSOCIATIONS
    //---------------------------------------,

    onSignalPageChange(page) {
      if (this.signalSearchTerm && this.signalSearchTerm.trim()) {
        this.searchSignals(this.signalSearchTerm, page);
      } else {
        this.loadAllSignals(page);
      }
    },

    setSignalCurrentVersion(signalId) {
      if (!this.currentGlobalTenant) {
        notify( { message: "Please select a tenant first.", isError: true });
        return;
      }

      const signal = this.signals.find(s => s.id === signalId);
      if (!signal) return;

      api.request(`/ui/signals/${signalId}/toggle_active`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: signal.tenant_id,
          name: signal.name,
          signal_id: signalId
        })
      })
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
          }
          return response.json();
        })
        .then(() => {
          this.loadAllSignals(this.signalPage);
        })
        .catch(error => {
          console.error("Error setting current version:", error);
          notify( {
            message: "Error setting current version: " + error.message,
            isError: true
          });
        });
    }
  }
};
