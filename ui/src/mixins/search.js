import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    searchEntityType: "all",
    searchQuery: "",
    searchTenantsResults: [],
    tenantSearchPage: 1,
    tenantSearchSize: 5,
    tenantSearchTotal: 0,
    tenantSearchTotalPages: 1,
    expandedSearchTenants: {},
    searchTenantEdits: {},
    searchCheckpointsResults: [],
    checkpointSearchPage: 1,
    checkpointSearchSize: 5,
    checkpointSearchTotal: 0,
    checkpointSearchTotalPages: 1,
    expandedSearchCheckpoints: {},
    searchCheckpointEdits: {},
    searchSignalsResults: [],
    signalSearchPage: 1,
    signalSearchSize: 5,
    signalSearchTotal: 0,
    signalSearchTotalPages: 1,
    expandedSearchSignals: {},
    searchSignalEdits: {},
    searchDecisionsResults: [],
    decisionSearchPage: 1,
    decisionSearchSize: 5,
    decisionSearchTotal: 0,
    decisionSearchTotalPages: 1,
    expandedSearchDecisions: {},
    decisionSearchFromDate: "",
    decisionSearchToDate: "",
    searchSignalLogsResults: [],
    signalLogsSearchPage: 1,
    signalLogsSearchSize: 5,
    signalLogsSearchTotal: 0,
    signalLogsSearchTotalPages: 1,
    expandedSearchSignalLogs: {},
    searchDecisionDetails: {}
    };
  },
  methods: {
    doSearch(page) {
      if (this.searchEntityType === "tenants" || this.searchEntityType === "all") {
        this.tenantSearchPage = page;
        this.searchTenantsResults = [];
      }
      if (this.searchEntityType === "checkpoints" || this.searchEntityType === "all") {
        this.checkpointSearchPage = page;
        this.searchCheckpointsResults = [];
      }
      if (this.searchEntityType === "signals" || this.searchEntityType === "all") {
        this.signalSearchPage = page;
        this.searchSignalsResults = [];
      }
      if (this.searchEntityType === "decisions") {
        this.decisionSearchPage = page;
        this.searchDecisionsResults = [];
      }
      if (this.searchEntityType === "signal_logs") {
        this.signalLogsSearchPage = page;
        this.searchSignalLogsResults = [];
      }
      this.fetchSearchResults();
    },

    fetchSearchResults() {
      const qEnc = encodeURIComponent(this.searchQuery);

      // Tenants
      if (this.searchEntityType === "tenants" || this.searchEntityType === "all") {
        const url = `/ui/search_tenants?q=${qEnc}&page=${this.tenantSearchPage}&size=${this.tenantSearchSize}`;
        api.request(url)
          .then(r => r.json())
          .then(data => {
            this.searchTenantsResults = data.items;
            this.tenantSearchTotal = data.total;
            this.tenantSearchTotalPages = Math.ceil(data.total / this.tenantSearchSize);
            this.searchTenantsResults.forEach(t => {
              this.expandedSearchTenants[t.id] = false;
              this.searchTenantEdits[t.id] = { name: t.name };
            });
          });
      }
      // Checkpoints
      if (this.searchEntityType === "checkpoints" || this.searchEntityType === "all") {
        const url = `/ui/search_checkpoints?q=${qEnc}&page=${this.checkpointSearchPage}&size=${this.checkpointSearchSize}`;
        api.request(url)
          .then(r => r.json())
          .then(data => {
            this.searchCheckpointsResults = data.items;
            this.checkpointSearchTotal = data.total;
            this.checkpointSearchTotalPages = Math.ceil(data.total / this.checkpointSearchSize);
            this.searchCheckpointsResults.forEach(cp => {
              this.expandedSearchCheckpoints[cp.id] = false;
              this.searchCheckpointEdits[cp.id] = {
                name: cp.name,
                dsl_expression: cp.dsl_expression
              };
            });
          });
      }
      // Signals
      if (this.searchEntityType === "signals" || this.searchEntityType === "all") {
        const url = `/ui/search_signals?q=${qEnc}&page=${this.signalSearchPage}&size=${this.signalSearchSize}`;
        api.request(url)
          .then(r => r.json())
          .then(data => {
            this.searchSignalsResults = data.items;
            this.signalSearchTotal = data.total;
            this.signalSearchTotalPages = Math.ceil(data.total / this.signalSearchSize);
            this.searchSignalsResults.forEach(s => {
              this.expandedSearchSignals[s.id] = false;
              this.searchSignalEdits[s.id] = {
                name: s.name,
                method_of_call: s.method_of_call
              };
            });
          });
      }
      // Decisions
      if (this.searchEntityType === "decisions") {
        let url = `/ui/search_decisions?q=${qEnc}&page=${this.decisionSearchPage}&size=${this.decisionSearchSize}`;
        if (this.decisionSearchFromDate) {
          url += `&from_date=${encodeURIComponent(this.decisionSearchFromDate)}`;
        }
        if (this.decisionSearchToDate) {
          url += `&to_date=${encodeURIComponent(this.decisionSearchToDate)}`;
        }
        api.request(url)
          .then(r => r.json())
          .then(data => {
            this.searchDecisionsResults = data.items;
            this.decisionSearchTotal = data.total;
            this.decisionSearchTotalPages = Math.ceil(data.total / this.decisionSearchSize);
            this.searchDecisionsResults.forEach(d => {
              this.expandedSearchDecisions[d.id] = false;
            });
          });
      }
      // Signal logs
      if (this.searchEntityType === "signal_logs") {
        let url = `/ui/search_signal_logs?q=${qEnc}&page=${this.signalLogsSearchPage}&size=${this.signalLogsSearchSize}`;
        api.request(url)
          .then(r => r.json())
          .then(data => {
            this.searchSignalLogsResults = data.items;
            this.signalLogsSearchTotal = data.total;
            this.signalLogsSearchTotalPages = Math.ceil(data.total / this.signalLogsSearchSize);
            this.searchSignalLogsResults.forEach(log => {
              this.expandedSearchSignalLogs[log.id] = false;
              if (!log.param_values) {
                log.param_values = [];
              }
            });
          });
      }
    },
    // Tenants search pagination,

    nextTenantSearch() {
      if (this.tenantSearchPage < this.tenantSearchTotalPages) {
        this.tenantSearchPage++;
        this.fetchSearchResults();
      }
    },

    prevTenantSearch() {
      if (this.tenantSearchPage > 1) {
        this.tenantSearchPage--;
        this.fetchSearchResults();
      }
    },
    // Checkpoints search pagination,

    nextCheckpointSearch() {
      if (this.checkpointSearchPage < this.checkpointSearchTotalPages) {
        this.checkpointSearchPage++;
        this.fetchSearchResults();
      }
    },

    prevCheckpointSearch() {
      if (this.checkpointSearchPage > 1) {
        this.checkpointSearchPage--;
        this.fetchSearchResults();
      }
    },
    // Signals search pagination,

    nextSignalSearch() {
      if (this.signalSearchPage < this.signalSearchTotalPages) {
        this.signalSearchPage++;
        this.fetchSearchResults();
      }
    },

    prevSignalSearch() {
      if (this.signalSearchPage > 1) {
        this.signalSearchPage--;
        this.fetchSearchResults();
      }
    },
    // Decision search pagination,

    nextDecisionSearch() {
      if (this.decisionSearchPage < this.decisionSearchTotalPages) {
        this.decisionSearchPage++;
        this.fetchSearchResults();
      }
    },

    prevDecisionSearch() {
      if (this.decisionSearchPage > 1) {
        this.decisionSearchPage--;
        this.fetchSearchResults();
      }
    },
    // Signal logs search pagination,

    nextSignalLogsSearch() {
      if (this.signalLogsSearchPage < this.signalLogsSearchTotalPages) {
        this.signalLogsSearchPage++;
        this.fetchSearchResults();
      }
    },

    prevSignalLogsSearch() {
      if (this.signalLogsSearchPage > 1) {
        this.signalLogsSearchPage--;
        this.fetchSearchResults();
      }
    },

    toggleExpandSearchTenant(tid) {
      this.expandedSearchTenants[tid] = !this.expandedSearchTenants[tid];
    },

    saveSearchTenant(tid) {
      const e = this.searchTenantEdits[tid];
      api.request(`/ui/tenants/${tid}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: e.name })
      })
        .then(async resp => {
          if (!resp.ok) {
            const txt = await resp.text();
            throw new Error("Failed to update tenant: " + txt);
          }
          return resp.json();
        })
        .then(u => {
          this.expandedSearchTenants[tid] = false;
          this.doSearch(this.tenantSearchPage);
        })
        .catch(err => console.error(err));
    },

    toggleExpandSearchCheckpoint(cpId) {
      this.expandedSearchCheckpoints[cpId] = !this.expandedSearchCheckpoints[cpId];
    },

    saveSearchCheckpoint(cpId) {
      const e = this.searchCheckpointEdits[cpId];
      api.request(`/ui/checkpoints/${cpId}`)
        .then(r => r.json())
        .then(found => {
          const payload = {
            tenant_id: found.tenant_id,
            name: e.name,
            description: found.description || "",
            type: found.type || "",
            dsl_expression: e.dsl_expression,
            method_of_call: found.method_of_call,
            max_cost: found.max_cost,
            override_cost_flag: found.override_cost_flag,
            timeout_seconds: found.timeout_seconds
          };
          return api.request(`/ui/checkpoints/${cpId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        })
        .then(async resp => {
          if (!resp.ok) {
            const txt = await resp.text();
            throw new Error("Failed to update checkpoint: " + txt);
          }
          return resp.json();
        })
        .then(updated => {
          this.expandedSearchCheckpoints[cpId] = false;
          this.doSearch(this.checkpointSearchPage);
        })
        .catch(err => console.error(err));
    },

    toggleExpandSearchSignal(sid) {
      this.expandedSearchSignals[sid] = !this.expandedSearchSignals[sid];
    },

    saveSearchSignal(sid) {
      const e = this.searchSignalEdits[sid];
      api.request(`/ui/signals/${sid}`)
        .then(r => r.json())
        .then(original => {
          const payload = {
            tenant_id: original.tenant_id,
            name: e.name,
            description: original.description,
            type: original.type,
            method_of_call: e.method_of_call || original.method_of_call,
            expression_body: original.expression_body,
            cost: e.cost || original.cost,
            cache_expiration_seconds: original.cache_expiration_seconds,
            timeout_seconds: original.timeout_seconds,
            can_run_in_parallel: original.can_run_in_parallel,
            order_of_evaluation: original.order_of_evaluation,
            http_method: original.http_method,
            request_url_params_template: original.request_url_params_template,
            request_body_template: original.request_body_template,
            request_headers_template: original.request_headers_template,
            allow_caching: original.allow_caching,
            global_reuse: original.global_reuse,
            function_params_template: original.function_params_template,
            makeCurrentVersion: this.makeCurrentVersion
          };
          return api.request("/ui/signals", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        })
        .then(async resp => {
          if (!resp.ok) {
            const txt = await resp.text();
            throw new Error("Failed to update signal: " + txt);
          }
          return resp.json();
        })
        .then(u => {
          this.expandedSearchSignals[sid] = false;
          this.doSearch(this.signalSearchPage);
        })
        .catch(err => console.error(err));
    },

    toggleExpandSearchDecision(did) {
      this.expandedSearchDecisions[did] = !this.expandedSearchDecisions[did];
      if (this.expandedSearchDecisions[did] && !this.searchDecisionDetails[did]) {
        this.fetchDecisionDetails(did);
      }
    },

    fetchDecisionDetails(decisionId) {
      api.decisions.get(decisionId)
        .then(decisionData => {
          this.searchDecisionDetails[decisionId] = decisionData;
        })
        .catch(err => {
          console.error("Error fetching decision details:", err);
        });
    },

    toggleExpandSearchSignalLog(logId) {
      this.expandedSearchSignalLogs[logId] = !this.expandedSearchSignalLogs[logId];
    },

    //---------------------------------------
    // TEST DECISIONS
    //---------------------------------------,

    onSearchSignalPageChange(page) {
      this.signalSearchPage = page;
      const qEnc = encodeURIComponent(this.searchQuery);
      let url = `/ui/search_signals?q=${qEnc}&page=${page}&size=${this.signalSearchSize}`;
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
          this.searchSignalsResults = data.items;
          this.signalSearchTotal = data.total;
          this.signalSearchTotalPages = Math.ceil(data.total / this.signalSearchSize);
        })
        .catch(err => {
          console.error("Error fetching search signals:", err);
          this.searchSignalsResults = [];
          this.signalSearchTotal = 0;
          this.signalSearchTotalPages = 1;
        });
    },
    // Add method for checkpoint signal pagination
  }
};
