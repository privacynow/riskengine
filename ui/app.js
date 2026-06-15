// Import the SignalDetails component
// import SignalDetails from './components/SignalDetails.vue';

new Vue({
  el: "#app",
  components: {},
  data: {
    // Current view
    view: "home",
    isVueReady: false,
    showSignalConfirmation: false,

    // For version checking
    isCurrentVersion: function(checkpoint) {
      return checkpoint && checkpoint.is_current_version === true;
    },

    // Global current tenant
    currentGlobalTenant: null,

    // -----------------------------
    // TENANTS
    // -----------------------------
    tenantSearchTerm: "",
    newTenantName: "",
    showTenantCreateForm: false,
    copyFromTenantId: "", // For copying tenant data

    tenants: [],
    tenantPage: 1,
    tenantSize: 5,
    tenantTotal: 0,
    tenantTotalPages: 1,

    expandedTenants: {},    // { tenantId: bool }
    tenantEdits: {},        // { tenantId: { name: "..." } }

    // -----------------------------
    // CHECKPOINTS
    // -----------------------------
    checkpointsActiveFilter: "all",
    checkpointSearchTerm: "",
    showCheckpointCreateForm: false,
    makeNewVersionCurrent: false, // Flag for making new version current
    makeCurrentVersion: false, // Flag for making new checkpoint current
    existingCheckpoint: null, // For storing existing checkpoint details
    showCheckpointConfirmation: false, // For showing confirmation dialog

    checkpoints: [],
    checkpointPage: 1,
    checkpointSize: 5,
    checkpointTotal: 0,
    checkpointTotalPages: 1,

    expandedCheckpoints: {},
    checkpointEdits: {},

    newCheckpointName: "",
    newCheckpointDescription: "",
    newCheckpointType: "",
    newCheckpointDsl: "",
    checkpointCreated: false,
    createdCheckpointId: "",

    createCheckpointSignalSearch: "",
    createCheckpointSignalsList: [],
    createCheckpointSignalsPage: 1,
    createCheckpointSignalsSize: 5,
    createCheckpointSignalsTotal: 0,
    createCheckpointSignalsTotalPages: 1,
    expandedCreateCPSignals: {},

    // For editing existing checkpoint -> associate signals
    checkpointSignalSearch: {}, // { cpId: "search term" }
    checkpointSignalCandidates: {}, // { cpId: [ {id, name, ...} ] }
    checkpointSignalCandidatePage: {},
    checkpointSignalCandidateSize: 5,
    checkpointSignalCandidateTotal: {},
    checkpointSignalCandidateTotalPages: {},
    expandedCheckpointCandidate: {}, // { cpId: { candidateSignalId: bool } }

    // -----------------------------
    // SIGNALS
    // -----------------------------
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

    // For editing existing signals -> associate checkpoints
    signalCheckpointSearch: {}, // { signalId: "term" }
    signalCheckpointCandidates: {}, // { signalId: [ {id, name, ...} ] }
    signalCheckpointCandidatePage: {},
    signalCheckpointCandidateSize: 5,
    signalCheckpointCandidateTotal: {},
    signalCheckpointCandidateTotalPages: {},
    expandedSignalCandidate: {}, // { signalId: { checkpointId: bool } }

    // -----------------------------
    // ALL Tenants for selects
    // -----------------------------
    allTenants: [],

    // -----------------------------
    // ASSOCIATIONS
    // -----------------------------
    assocTenantFilter: "",
    assocMode: "checkpoint", // 'checkpoint' or 'signal'

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
    expandedAssocSignalCandidate: {},

    // -----------------------------
    // SEARCH
    // -----------------------------
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

    // >>> New for decision details expansion <<<
    searchDecisionDetails: {}, // { decisionId: { checkpoint_name, signals[], etc. } }

    // -----------------------------
    // TEST DECISIONS
    // -----------------------------
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
    testDecAssocSignals: {}, // { cpId: [ signal objects ] }
    expandedTestDecSignals: {}, // { cpId: { sigId: bool } }
    testDecParams: {}, // { cpId: { sigId: { param: val, ... } } }
    testDecResponses: {},

    // Add new checkpoint data structure
    newCheckpointData: {
      name: '',
      description: '',
      type: '',  // Remove default value
      dsl_expression: '',
      makeCurrentVersion: false,
      signalSearch: '',
      signalSearchResults: [],
      associatedSignals: [],
      signalPage: 1,
      signalTotalPages: 1,
      signalSize: 5
    },

    // Add newSignalData structure
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
    },
  },
  methods: {
    //---------------------------------------
    // Navigation
    //---------------------------------------
    refreshSignals(signalId = null) {
      if (signalId) {
        // Just update a single signal's status
        this.loadAllSignals(this.signalPage, signalId);
      } else if (this.signalSearchTerm && this.signalSearchTerm.trim()) {
        this.searchSignals(this.signalSearchTerm, this.signalPage);
      } else {
        this.loadAllSignals(this.signalPage);
      }
    },
    switchView(newView) {
      this.view = newView;
      if (newView === "tenants") {
        this.fetchAllTenants();
        this.fetchTenants(1);
      } else if (newView === "checkpoints") {
        this.fetchAllTenants();
        this.loadAllCheckpoints(1);
      } else if (newView === "signals") {
        this.fetchAllTenants();
        this.loadAllSignals(1);
      } else if (newView === "associations") {
        this.fetchAllTenants();
        this.resetAssociationsData();
      } else if (newView === "decisionTest") {
        this.fetchAllTenants();
        this.testDecCheckpoints = [];
      }
    },
    resetAssociationsData() {
      this.assocCheckpointSearchTerm = "";
      this.assocSignalSearchTerm = "";
      this.assocCheckpoints = [];
      this.assocSignals = [];
      this.assocCheckpointPage = 1;
      this.assocSignalPage = 1;
      this.assocCheckpointMap = {};
      this.assocSignalMap = {};
    },

    //---------------------------------------
    // UTILS
    //---------------------------------------
    fetchAllTenants() {
      fetch("/ui/tenants?page=1&size=9999")
        .then(r => r.json())
        .then(data => {
          this.allTenants = data.items || [];
        })
        .catch(err => console.error("Error fetching allTenants:", err));
    },

    //---------------------------------------
    // TENANTS
    //---------------------------------------
    toggleTenantCreateForm() {
      this.showTenantCreateForm = !this.showTenantCreateForm;
    },
    fetchTenants(page) {
      this.tenantPage = page;
      const url = `/ui/tenants?page=${page}&size=${this.tenantSize}`;
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.tenants = data.items;
          this.tenantTotal = data.total;
          this.tenantTotalPages = Math.ceil(data.total / this.tenantSize);
        })
        .catch(err => console.error("Error fetching tenants", err));
    },
    nextTenantPage() {
      if (this.tenantPage < this.tenantTotalPages) {
        this.fetchTenants(this.tenantPage + 1);
      }
    },
    prevTenantPage() {
      if (this.tenantPage > 1) {
        this.fetchTenants(this.tenantPage - 1);
      }
    },
    searchTenants(page) {
      this.tenantPage = page;
      const q = encodeURIComponent(this.tenantSearchTerm.trim());
      if (!q) {
        this.fetchTenants(page);
        return;
      }
      const url = `/ui/search_tenants?q=${q}&page=${page}&size=${this.tenantSize}`;
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.tenants = data.items;
          this.tenantTotal = data.total;
          this.tenantTotalPages = Math.ceil(data.total / this.tenantSize);
        })
        .catch(err => console.error("Error searching tenants:", err));
    },
    createTenant() {
      const payload = { 
        name: this.newTenantName,
        copyFromTenantId: this.copyFromTenantId 
      };
      fetch("/ui/tenants", {
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
          this.newTenantName = "";
          this.copyFromTenantId = "";  // Reset the copyFromTenantId
          this.showTenantCreateForm = false;
          this.fetchTenants(this.tenantPage);
        })
        .catch(err => {
          console.error("Error creating tenant:", err);
          alert('Error creating tenant: ' + err.message);
        });
    },
    toggleExpandTenant(tenantId) {
      this.expandedTenants[tenantId] = !this.expandedTenants[tenantId];
    },
    saveTenant(tenantId) {
      if (!this.tenantEdits[tenantId]) return;
      
      const payload = {
        name: this.tenantEdits[tenantId].name,
        copyFromTenantId: this.copyFromTenantId
      };

      fetch(`/ui/tenants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          alert(data.error);
          return;
        }
          this.fetchTenants(this.tenantPage);
        delete this.tenantEdits[tenantId];
        this.expandedTenants[tenantId] = false;
      });
    },

    //---------------------------------------
    // CHECKPOINTS
    //---------------------------------------
    toggleCheckpointCreateForm() {
      this.showCheckpointCreateForm = !this.showCheckpointCreateForm;
    },
    async loadAllCheckpoints(page) {
      try {
        if (!this.currentGlobalTenant) {
          this.checkpoints = [];
          this.checkpointTotal = 0;
          this.checkpointTotalPages = 1;
          this.checkpointPage = 1;
          return;
        }

        // Reset search term when explicitly loading all
        this.checkpointSearchTerm = "";

        let url = `/ui/checkpoints?page=${page}&size=${this.checkpointSize}&tenant_id=${this.currentGlobalTenant.id}`;
        if (this.checkpointsActiveFilter === 'active') {
          url += '&active_only=true';
        }
        
      fetch(url)
          .then(response => {
            if (!response.ok) {
              throw new Error('Failed to fetch checkpoints');
            }
            return response.json();
          })
        .then(data => {
          this.checkpoints = data.items;
          this.checkpointTotal = data.total;
          this.checkpointTotalPages = Math.ceil(data.total / this.checkpointSize);
            this.checkpointPage = page;

            // Initialize checkpoint edits for each checkpoint
          this.checkpoints.forEach(cp => {
            this.$set(this.checkpointEdits, cp.id, {
              name: cp.name,
                description: cp.description || '',
                type: cp.type || '',
                dsl_expression: cp.dsl_expression || '',
                makeCurrentVersion: false
              });
              this.$set(this.expandedCheckpoints, cp.id, false);
          });
        })
          .catch(error => {
            console.error('Error loading checkpoints:', error);
          });
      } catch (error) {
        console.error('Error in loadAllCheckpoints:', error);
      }
    },
    searchCheckpoints(page) {
      if (!this.currentGlobalTenant) {
        this.checkpoints = [];
        this.checkpointTotal = 0;
        this.checkpointTotalPages = 1;
        this.checkpointPage = 1;
        return;
      }

      this.checkpointPage = page;
      const q = encodeURIComponent(this.checkpointSearchTerm.trim());
      if (!q) {
        this.loadAllCheckpoints(page);
        return;
      }

      let url = `/ui/search_checkpoints?q=${q}&page=${page}&size=${this.checkpointSize}&tenant_id=${this.currentGlobalTenant.id}`;
      if (this.checkpointsActiveFilter === 'active') {
        url += '&active_only=true';
      }

      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.checkpoints = data.items;
          this.checkpointTotal = data.total;
          this.checkpointTotalPages = Math.ceil(data.total / this.checkpointSize);
          this.checkpoints.forEach(cp => {
            this.$set(this.expandedCheckpoints, cp.id, false);
            this.$set(this.checkpointEdits, cp.id, {
              name: cp.name,
              description: cp.description,
              type: cp.type,
              dsl_expression: cp.dsl_expression,
              method_of_call: cp.method_of_call,
              max_cost: cp.max_cost,
              override_cost_flag: cp.override_cost_flag,
              timeout_seconds: cp.timeout_seconds,
              associatedSignals: []
            });
            this.$set(this.checkpointSignalSearch, cp.id, "");
            this.$set(this.checkpointSignalCandidates, cp.id, []);
            this.$set(this.checkpointSignalCandidatePage, cp.id, 1);
            this.$set(this.checkpointSignalCandidateTotal, cp.id, 0);
            this.$set(this.checkpointSignalCandidateTotalPages, cp.id, 1);
            this.$set(this.expandedCheckpointCandidate, cp.id, {});
          });
          this.checkpoints.forEach(cp => {
            this.loadCheckpointAssociations(cp.id);
          });
        })
        .catch(err => console.error("Error searching checkpoints:", err));
    },
    nextCheckpointPage() {
      if (this.checkpointPage < this.checkpointTotalPages) {
        this.loadAllCheckpoints(this.checkpointPage + 1);
      }
    },
    prevCheckpointPage() {
      if (this.checkpointPage > 1) {
        this.loadAllCheckpoints(this.checkpointPage - 1);
      }
    },
    toggleExpandCheckpoint(cpId) {
      this.expandedCheckpoints[cpId] = !this.expandedCheckpoints[cpId];
    },
    loadCheckpointAssociations(cpId) {
      fetch(`/ui/signals?checkpoint_id=${cpId}&page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const items = data.items || [];
          this.checkpointEdits[cpId].associatedSignals = items;
        })
        .catch(err => console.error(`Error fetching signals for checkpoint ${cpId}`, err));
    },
    removeSignalAssociation(cpId, sigId) {
      // We'll fetch all checkpoint_signals then remove
      fetch(`/ui/checkpoint_signals?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const assoc = data.items.find(a => a.checkpoint_id === cpId && a.signal_id === sigId);
          if (!assoc) {
            alert("Association not found. Possibly already removed.");
            return;
          }
          return fetch(`/ui/checkpoint_signals/${assoc.id}`, { method: "DELETE" });
        })
        .then(resp => {
          if (!resp) return;
          if (!resp.ok) {
            throw new Error("Failed to remove association.");
          }
          this.loadCheckpointAssociations(cpId);
        })
        .catch(err => console.error("Error removing signal association:", err));
    },
    saveCheckpoint(cpId) {
      if (!this.checkpointEdits[cpId]) return;
      
      const checkpoint = this.checkpoints.find(cp => cp.id === cpId);
      if (!checkpoint) return;

          const payload = {
        ...this.checkpointEdits[cpId],
        tenant_id: checkpoint.tenant_id,
        name: checkpoint.name
      };

      fetch(`/ui/checkpoints/${cpId}`, {
        method: 'PUT',
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
        // Instead of deleting the edit state, reinitialize it
        this.$set(this.checkpointEdits, cpId, {
          name: checkpoint.name,
          description: checkpoint.description,
          type: checkpoint.type,
          dsl_expression: checkpoint.dsl_expression,
          method_of_call: checkpoint.method_of_call,
          max_cost: checkpoint.max_cost,
          override_cost_flag: checkpoint.override_cost_flag,
          timeout_seconds: checkpoint.timeout_seconds,
          associatedSignals: []
        });
          this.expandedCheckpoints[cpId] = false;
        this.makeCurrentVersion = false;
          this.loadAllCheckpoints(this.checkpointPage);
        })
      .catch(error => {
        console.error('Error saving checkpoint:', error);
        alert('Error saving checkpoint: ' + error.message);
      });
    },
    addSignalToCheckpoint(signalId) {
      const signal = this.newCheckpointData.signalSearchResults.find(s => s.id === signalId);
      if (signal) {
        if (!this.newCheckpointData.associatedSignals.some(s => s.id === signalId)) {
          this.newCheckpointData.associatedSignals.push(signal);
        }
      }
    },

    removeSignalFromCheckpoint(signalId) {
      this.newCheckpointData.associatedSignals = this.newCheckpointData.associatedSignals.filter(s => s.id !== signalId);
    },

    createCheckpoint() {
      // Validate required fields
      if (!this.checkpointsTenantFilter) {
        alert("Please select a tenant first.");
        return;
      }
      if (!this.newCheckpointData.name) {
        alert("Checkpoint name is required.");
        return;
      }
      if (!this.newCheckpointData.type) {
        alert("Checkpoint type is required.");
        return;
      }
      if (!this.newCheckpointData.dsl_expression) {
        alert("DSL expression is required.");
        return;
      }

      const payload = {
        tenant_id: this.checkpointsTenantFilter,
        name: this.newCheckpointData.name,
        description: this.newCheckpointData.description || "",
        type: this.newCheckpointData.type,
        dsl_expression: this.newCheckpointData.dsl_expression,
        makeCurrentVersion: this.newCheckpointData.makeCurrentVersion,
        signals: (this.newCheckpointData.associatedSignals || []).map(s => s.id)
      };

      // First check if a checkpoint with this name already exists
      const url = `/ui/search_checkpoints?q=${encodeURIComponent(this.newCheckpointData.name)}&tenant_id=${this.checkpointsTenantFilter}&page=1&size=1`;
      
      fetch(url)
        .then(r => {
          if (!r.ok) {
            return r.text().then(text => { throw new Error(text); });
          }
          return r.json();
        })
        .then(data => {
          // Check if any checkpoints exist with the same name
          const existingCheckpoint = data.items && data.items.length > 0 ? 
            data.items.filter(cp => cp.name === this.newCheckpointData.name) : null;
          
          if (existingCheckpoint) {
            this.existingCheckpoint = existingCheckpoint;
            this.showCheckpointConfirmation = true;
            throw 'checkpoint_exists';
          }
          
          return fetch("/ui/checkpoints", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        })
        .then(r => {
          if (!r.ok) {
            return r.text().then(text => { throw new Error(text); });
          }
          return r.json();
        })
        .then(created => {
          // Reset form data
          this.newCheckpointData = {
            name: '',
            description: '',
            type: '',
            dsl_expression: '',
            makeCurrentVersion: false,
            signalSearch: '',
            signalSearchResults: [],
            associatedSignals: [],
            signalPage: 1,
            signalTotalPages: 1,
            signalSize: 5
          };
          this.showCheckpointCreateForm = false;
          this.loadAllCheckpoints(this.checkpointPage);
        })
        .catch(err => {
          if (err === 'checkpoint_exists') return;
          console.error("Error creating checkpoint:", err);
          alert('Error creating checkpoint: ' + err.message);
        });
    },
    confirmCheckpointCreation() {
      const payload = {
        tenant_id: this.checkpointsTenantFilter,
        name: this.newCheckpointData.name,
        description: this.newCheckpointData.description || "",
        type: this.newCheckpointData.type,
        dsl_expression: this.newCheckpointData.dsl_expression,
        makeCurrentVersion: this.newCheckpointData.makeCurrentVersion,
        signals: this.newCheckpointData.associatedSignals.map(s => s.id)
      };
      
      fetch("/ui/checkpoints", {
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
          this.createdCheckpointId = created.id;
          this.checkpointCreated = true;
          // Reset form data
          this.newCheckpointData = {
            name: '',
            description: '',
            type: '',
            dsl_expression: '',
            makeCurrentVersion: false,
            signalSearch: '',
            signalSearchResults: [],
            associatedSignals: [],
            signalPage: 1,
            signalTotalPages: 1,
            signalSize: 5
          };
          this.showCheckpointCreateForm = false;
          this.showCheckpointConfirmation = false;
          this.existingCheckpoint = null;
          this.loadAllCheckpoints(this.checkpointPage);
        })
        .catch(err => {
          console.error("Error creating checkpoint:", err);
          alert('Error creating checkpoint: ' + err.message);
          this.showCheckpointConfirmation = false;
          this.existingCheckpoint = null;
        });
    },
    cancelCheckpointCreation() {
      this.showCheckpointConfirmation = false;
      this.existingCheckpoint = null;
    },
    fetchCheckpointSignalSearch(page) {
      const searchTerm = this.newCheckpointData.signalSearch.trim();
      
      // If no search term, fall back to loading all signals
      if (!searchTerm) {
        this.loadAllSignalsForCheckpoint(page);
        return;
      }
      
      // Clear results if no tenant filter
      if (!this.checkpointsTenantFilter) {
        this.newCheckpointData.signalSearchResults = [];
        this.newCheckpointData.signalPage = page;
        this.newCheckpointData.signalTotalPages = 1;
        return;
      }

      // Construct URL with proper query parameters
      const params = new URLSearchParams({
        q: searchTerm,
        page: page,
        size: this.newCheckpointData.signalSize,
        tenant_id: this.checkpointsTenantFilter
      });
      
      if (this.signalsActiveFilter === 'active') {
        params.append('active_only', 'true');
      }
      
      const url = `/ui/search_signals?${params.toString()}`;
      
      fetch(url)
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => {
              throw new Error(`Failed to fetch signals: ${text}`);
            });
          }
          return response.json();
        })
        .then(data => {
          // Ensure data has expected structure
          if (!data || !Array.isArray(data.items)) {
            throw new Error('Invalid response format from server');
          }
          
          this.newCheckpointData.signalSearchResults = data.items.map(signal => ({
            ...signal,
            selected: this.newCheckpointData.associatedSignals.some(s => s.id === signal.id)
          }));
          this.newCheckpointData.signalPage = page;
          this.newCheckpointData.signalTotalPages = Math.ceil((data.total || 0) / this.newCheckpointData.signalSize);
        })
        .catch(err => {
          console.error("Error searching signals for checkpoint:", err);
          // Reset to safe state on error
          this.newCheckpointData.signalSearchResults = [];
          this.newCheckpointData.signalPage = page;
          this.newCheckpointData.signalTotalPages = 1;
        });
    },
    loadAllSignalsForCheckpoint(page) {
      // Clear results if no tenant filter
      if (!this.checkpointsTenantFilter) {
        this.newCheckpointData.signalSearchResults = [];
        this.newCheckpointData.signalPage = parseInt(page) || 1;
        this.newCheckpointData.signalTotalPages = 1;
        return;
      }

      // Ensure page is a valid integer
      const pageNum = parseInt(page) || 1;

      // Construct URL with proper query parameters
      const params = new URLSearchParams({
        page: pageNum,
        size: this.newCheckpointData.signalSize,
        tenant_id: this.checkpointsTenantFilter
      });
      
      if (this.signalsActiveFilter === 'active') {
        params.append('active_only', 'true');
      }
      
      const url = `/ui/signals?${params.toString()}`;
      
      fetch(url)
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => {
              throw new Error(`Failed to fetch signals: ${text}`);
            });
          }
          return response.json();
        })
        .then(data => {
          // Ensure data has expected structure
          if (!data || !Array.isArray(data.items)) {
            throw new Error('Invalid response format from server');
          }
          
          this.newCheckpointData.signalSearchResults = data.items.map(signal => ({
            ...signal,
            selected: this.newCheckpointData.associatedSignals.some(s => s.id === signal.id)
          }));
          this.newCheckpointData.signalPage = pageNum;
          this.newCheckpointData.signalTotalPages = Math.ceil((data.total || 0) / this.newCheckpointData.signalSize);
        })
        .catch(err => {
          console.error("Error loading signals for checkpoint:", err);
          // Reset to safe state on error
          this.newCheckpointData.signalSearchResults = [];
          this.newCheckpointData.signalPage = pageNum;
          this.newCheckpointData.signalTotalPages = 1;
        });
    },
    nextCreateCheckpointSignalSearch() {
      if (this.createCheckpointSignalsPage < this.createCheckpointSignalsTotalPages) {
        this.fetchCheckpointSignalSearch(this.createCheckpointSignalsPage + 1);
      }
    },
    prevCreateCheckpointSignalSearch() {
      if (this.createCheckpointSignalsPage > 1) {
        this.fetchCheckpointSignalSearch(this.createCheckpointSignalsPage - 1);
      }
    },
    toggleExpandCreateCheckpointSignal(sid) {
      this.expandedCreateCPSignals[sid] = !this.expandedCreateCPSignals[sid];
    },
    associateSignalToCreatedCheckpoint(signalId) {
      if (!this.createdCheckpointId) {
        alert("No checkpoint ID found. Create checkpoint first.");
        return;
      }
      const payload = {
        checkpoint_id: this.createdCheckpointId,
        signal_id: signalId
      };
      fetch("/ui/checkpoint_signals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(async resp => {
          if (!resp.ok) {
            const txt = await resp.text();
            throw new Error("Failed to associate signal: " + txt);
          }
          return resp.json();
        })
        .then(result => {
          alert("Signal associated!");
        })
        .catch(err => console.error(err));
    },
    fetchSignalsForCheckpointEdit(cpId, page) {
      this.checkpointSignalCandidatePage[cpId] = page;
      const q = encodeURIComponent(this.checkpointSignalSearch[cpId].trim());
      if (!q) {
        this.loadAllSignalsForCheckpointEdit(cpId, page);
        return;
      }
      let url = `/ui/search_signals?q=${q}&page=${page}&size=${this.checkpointSignalCandidateSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.checkpointSignalCandidates[cpId] = data.items || [];
          this.checkpointSignalCandidateTotal[cpId] = data.total;
          this.checkpointSignalCandidateTotalPages[cpId] = Math.ceil(data.total / this.checkpointSignalCandidateSize);
          this.checkpointSignalCandidates[cpId].forEach(s => {
            if (!this.expandedCheckpointCandidate[cpId]) {
              this.$set(this.expandedCheckpointCandidate, cpId, {});
            }
            this.$set(this.expandedCheckpointCandidate[cpId], s.id, false);
          });
        })
        .catch(err => console.error("Error searching signals for cp edit:", err));
    },
    loadAllSignalsForCheckpointEdit(cpId, page) {
      this.checkpointSignalCandidatePage[cpId] = page;
      let url = `/ui/signals?page=${page}&size=${this.checkpointSignalCandidateSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.checkpointSignalCandidates[cpId] = data.items || [];
          this.checkpointSignalCandidateTotal[cpId] = data.total;
          this.checkpointSignalCandidateTotalPages[cpId] = Math.ceil(data.total / this.checkpointSignalCandidateSize);
          this.checkpointSignalCandidates[cpId].forEach(s => {
            if (!this.expandedCheckpointCandidate[cpId]) {
              this.$set(this.expandedCheckpointCandidate, cpId, {});
            }
            this.$set(this.expandedCheckpointCandidate[cpId], s.id, false);
          });
        })
        .catch(err => console.error("Error loading all signals for cp edit:", err));
    },
    toggleExpandCheckpointCandidate(cpId, sid) {
      this.expandedCheckpointCandidate[cpId][sid] = !this.expandedCheckpointCandidate[cpId][sid];
    },
    nextCheckpointSignalCandidatePage(cpId) {
      if (this.checkpointSignalCandidatePage[cpId] < this.checkpointSignalCandidateTotalPages[cpId]) {
        this.fetchSignalsForCheckpointEdit(cpId, this.checkpointSignalCandidatePage[cpId] + 1);
      }
    },
    prevCheckpointSignalCandidatePage(cpId) {
      if (this.checkpointSignalCandidatePage[cpId] > 1) {
        this.fetchSignalsForCheckpointEdit(cpId, this.checkpointSignalCandidatePage[cpId] - 1);
      }
    },
    associateSignalToCheckpoint(cpId, sigId) {
      const payload = { checkpoint_id: cpId, signal_id: sigId };
      fetch("/ui/checkpoint_signals", {
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
          this.loadCheckpointAssociations(cpId);
        })
        .catch(err => console.error("Error associating signal to checkpoint:", err));
    },

    //---------------------------------------
    // SIGNALS
    //---------------------------------------
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
      
      fetch(`/ui/signals?${params.toString()}`)
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
                this.$set(this.signals, index, updatedSignal);
              }
            }
          } else {
            // Full reload
          this.signals = data.items;
          this.signalTotal = data.total;
          this.signalTotalPages = Math.ceil(data.total / this.signalSize);
          this.signals.forEach(s => {
            this.$set(this.expandedSignals, s.id, false);
            this.$set(this.signalEdits, s.id, {
              name: s.name,
              description: s.description,
              method_of_call: s.method_of_call,
              cost: s.cost,
              associatedCheckpoints: []
            });
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
      fetch(url)
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
            this.$set(this.expandedSignals, s.id, false);
            this.$set(this.signalEdits, s.id, {
              name: s.name,
              description: s.description,
              method_of_call: s.method_of_call,
              cost: s.cost,
              associatedCheckpoints: []
            });
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
      fetch(`/ui/checkpoints?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const allCps = data.items;
          return fetch(`/ui/checkpoint_signals?page=1&size=9999`).then(r => r.json()).then(assocData => {
            const relevant = assocData.items.filter(a => a.signal_id === sid);
            const cpIds = relevant.map(r => r.checkpoint_id);
            const associatedCps = allCps.filter(cp => cpIds.includes(cp.id));
            this.signalEdits[sid].associatedCheckpoints = associatedCps;
          });
        })
        .catch(err => console.error("Error loading signal associations:", err));
    },
    removeCheckpointAssociation(sigId, cpId) {
      fetch(`/ui/checkpoint_signals?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const assoc = data.items.find(a => a.signal_id === sigId && a.checkpoint_id === cpId);
          if (!assoc) {
            alert("Association not found.");
            return;
          }
          return fetch(`/ui/checkpoint_signals/${assoc.id}`, { method: "DELETE" });
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
        alert("Please select a tenant first.");
        return;
      }
      
      const payload = {
        tenant_id: this.currentGlobalTenant.id,
        ...this.newSignalData
      };

      fetch("/ui/signals", {
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
          alert('Error creating signal: ' + err.message);
        });
    },
    toggleExpandSignal(sid) {
      this.$set(this.expandedSignals, sid, !this.expandedSignals[sid]);
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
        bearer_token: signal.bearer_token || "",
        allow_caching: signal.allow_caching || false,
        global_reuse: signal.global_reuse || false,
        function_params_template: signal.function_params_template || ""
      };

      fetch(`/ui/signals`, {
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
        alert('Error saving signal: ' + error.message);
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
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.signalCheckpointCandidates[sid] = data.items || [];
          this.signalCheckpointCandidateTotal[sid] = data.total;
          this.signalCheckpointCandidateTotalPages[sid] = Math.ceil(data.total / this.signalCheckpointCandidateSize);
          this.signalCheckpointCandidates[sid].forEach(cp => {
            if (!this.expandedSignalCandidate[sid]) {
              this.$set(this.expandedSignalCandidate, sid, {});
            }
            this.$set(this.expandedSignalCandidate[sid], cp.id, false);
          });
        })
        .catch(err => console.error("Error searching checkpoints for signal edit:", err));
    },
    loadAllCheckpointsForSignalEdit(sid, page) {
      this.signalCheckpointCandidatePage[sid] = page;
      const url = `/ui/checkpoints?page=${page}&size=${this.signalCheckpointCandidateSize}`;
      fetch(url)
        .then(r => r.json())
        .then(data => {
          this.signalCheckpointCandidates[sid] = data.items || [];
          this.signalCheckpointCandidateTotal[sid] = data.total;
          this.signalCheckpointCandidateTotalPages[sid] = Math.ceil(data.total / this.signalCheckpointCandidateSize);
          this.signalCheckpointCandidates[sid].forEach(cp => {
            if (!this.expandedSignalCandidate[sid]) {
              this.$set(this.expandedSignalCandidate, sid, {});
            }
            this.$set(this.expandedSignalCandidate[sid], cp.id, false);
          });
        })
        .catch(err => console.error("Error loading all checkpoints for signal edit:", err));
    },
    toggleExpandSignalCandidate(sid, cpId) {
      if (!this.expandedSignalCandidate[sid]) {
        this.$set(this.expandedSignalCandidate, sid, {});
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
      fetch("/ui/checkpoint_signals", {
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
    //---------------------------------------
    searchAssocCheckpoints(page) {
      this.assocCheckpointPage = page;
      const q = encodeURIComponent(this.assocCheckpointSearchTerm.trim());
      if (!q) {
        this.loadAllAssocCheckpoints(page);
        return;
      }
      const url = `/ui/search_checkpoints?q=${q}&page=${page}&size=${this.assocCheckpointSize}`;
      fetch(url)
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
            this.$set(this.expandedAssocCheckpoint, cp.id, false);
            this.loadAssocCheckpointMap(cp.id);
          });
        })
        .catch(err => console.error("Error searching assoc checkpoints:", err));
    },
    loadAllAssocCheckpoints(page) {
      this.assocCheckpointPage = page;
      let url = `/ui/checkpoints?page=${page}&size=${this.assocCheckpointSize}`;
      fetch(url)
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
            this.$set(this.expandedAssocCheckpoint, cp.id, false);
            this.loadAssocCheckpointMap(cp.id);
          });
        })
        .catch(err => console.error("Error loading all assoc checkpoints:", err));
    },
    toggleExpandAssocCheckpoint(cpId) {
      this.expandedAssocCheckpoint[cpId] = !this.expandedAssocCheckpoint[cpId];
    },
    loadAssocCheckpointMap(cpId) {
      fetch(`/ui/signals?checkpoint_id=${cpId}&page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          if (!this.assocCheckpointMap[cpId]) {
            this.$set(this.assocCheckpointMap, cpId, { signals: [] });
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
      fetch(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.$set(this.assocCheckpointCandidates, cpId, filtered);
          this.$set(this.assocCheckpointCandidateTotal, cpId, data.total);
          this.$set(this.assocCheckpointCandidateTotalPages, cpId, Math.ceil(data.total / this.assocCheckpointCandidateSize));
          if (!this.expandedAssocCheckpointCandidate[cpId]) {
            this.$set(this.expandedAssocCheckpointCandidate, cpId, {});
          }
          filtered.forEach(s => {
            this.$set(this.expandedAssocCheckpointCandidate[cpId], s.id, false);
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
      fetch(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(s => s.tenant_id === this.assocTenantFilter);
          }
          this.$set(this.assocCheckpointCandidates, cpId, filtered);
          this.$set(this.assocCheckpointCandidateTotal, cpId, data.total);
          this.$set(this.assocCheckpointCandidateTotalPages, cpId, Math.ceil(data.total / this.assocCheckpointCandidateSize));
          if (!this.expandedAssocCheckpointCandidate[cpId]) {
            this.$set(this.expandedAssocCheckpointCandidate, cpId, {});
          }
          filtered.forEach(s => {
            this.$set(this.expandedAssocCheckpointCandidate[cpId], s.id, false);
          });
        })
        .catch(err => console.error("Error loading signals to associate:", err));
    },
    toggleExpandAssocCheckpointCandidate(cpId, sid) {
      if (!this.expandedAssocCheckpointCandidate[cpId]) {
        this.$set(this.expandedAssocCheckpointCandidate, cpId, {});
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

    // By Signal
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
      fetch(url)
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
            this.$set(this.expandedAssocSignal, s.id, false);
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
      fetch(url)
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
            this.$set(this.expandedAssocSignal, s.id, false);
            this.loadAssocSignalMap(s.id);
          });
        })
        .catch(err => console.error("Error loading all assoc signals:", err));
    },
    toggleExpandAssocSignal(sid) {
      this.expandedAssocSignal[sid] = !this.expandedAssocSignal[sid];
    },
    loadAssocSignalMap(sid) {
      fetch(`/ui/checkpoints?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const allCps = data.items;
          return fetch(`/ui/checkpoint_signals?page=1&size=9999`).then(r => r.json()).then(assocData => {
            const relevant = assocData.items.filter(a => a.signal_id === sid);
            const cpIds = relevant.map(r => r.checkpoint_id);
            const associated = allCps.filter(cp => cpIds.includes(cp.id));
            if (!this.assocSignalMap[sid]) {
              this.$set(this.assocSignalMap, sid, { checkpoints: [] });
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
      fetch(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.$set(this.assocSignalCandidates, sid, filtered);
          this.$set(this.assocSignalCandidateTotal, sid, data.total);
          this.$set(this.assocSignalCandidateTotalPages, sid, Math.ceil(data.total / this.assocSignalCandidateSize));
          if (!this.expandedAssocSignalCandidate[sid]) {
            this.$set(this.expandedAssocSignalCandidate, sid, {});
          }
          filtered.forEach(cp => {
            this.$set(this.expandedAssocSignalCandidate[sid], cp.id, false);
          });
        })
        .catch(err => console.error("Error searching checkpoints to associate with signal:", err));
    },
    loadAllCheckpointsToAssociate(sid, page) {
      this.assocSignalCandidatePage[sid] = page;
      const url = `/ui/checkpoints?page=${page}&size=${this.assocSignalCandidateSize}`;
      fetch(url)
        .then(r => r.json())
        .then(data => {
          let filtered = data.items;
          if (this.assocTenantFilter) {
            filtered = filtered.filter(c => c.tenant_id === this.assocTenantFilter);
          }
          this.$set(this.assocSignalCandidates, sid, filtered);
          this.$set(this.assocSignalCandidateTotal, sid, data.total);
          this.$set(this.assocSignalCandidateTotalPages, sid, Math.ceil(data.total / this.assocSignalCandidateSize));
          if (!this.expandedAssocSignalCandidate[sid]) {
            this.$set(this.expandedAssocSignalCandidate, sid, {});
          }
          filtered.forEach(cp => {
            this.$set(this.expandedAssocSignalCandidate[sid], cp.id, false);
          });
        })
        .catch(err => console.error("Error loading all checkpoints to associate with signal:", err));
    },
    toggleExpandAssocSignalCandidate(sid, cpId) {
      if (!this.expandedAssocSignalCandidate[sid]) {
        this.$set(this.expandedAssocSignalCandidate, sid, {});
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
        fetch(url)
          .then(r => r.json())
          .then(data => {
            this.searchTenantsResults = data.items;
            this.tenantSearchTotal = data.total;
            this.tenantSearchTotalPages = Math.ceil(data.total / this.tenantSearchSize);
            this.searchTenantsResults.forEach(t => {
              this.$set(this.expandedSearchTenants, t.id, false);
              this.$set(this.searchTenantEdits, t.id, { name: t.name });
            });
          });
      }
      // Checkpoints
      if (this.searchEntityType === "checkpoints" || this.searchEntityType === "all") {
        const url = `/ui/search_checkpoints?q=${qEnc}&page=${this.checkpointSearchPage}&size=${this.checkpointSearchSize}`;
        fetch(url)
          .then(r => r.json())
          .then(data => {
            this.searchCheckpointsResults = data.items;
            this.checkpointSearchTotal = data.total;
            this.checkpointSearchTotalPages = Math.ceil(data.total / this.checkpointSearchSize);
            this.searchCheckpointsResults.forEach(cp => {
              this.$set(this.expandedSearchCheckpoints, cp.id, false);
              this.$set(this.searchCheckpointEdits, cp.id, {
                name: cp.name,
                dsl_expression: cp.dsl_expression
              });
            });
          });
      }
      // Signals
      if (this.searchEntityType === "signals" || this.searchEntityType === "all") {
        const url = `/ui/search_signals?q=${qEnc}&page=${this.signalSearchPage}&size=${this.signalSearchSize}`;
        fetch(url)
          .then(r => r.json())
          .then(data => {
            this.searchSignalsResults = data.items;
            this.signalSearchTotal = data.total;
            this.signalSearchTotalPages = Math.ceil(data.total / this.signalSearchSize);
            this.searchSignalsResults.forEach(s => {
              this.$set(this.expandedSearchSignals, s.id, false);
              this.$set(this.searchSignalEdits, s.id, {
                name: s.name,
                method_of_call: s.method_of_call
              });
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
        fetch(url)
          .then(r => r.json())
          .then(data => {
            this.searchDecisionsResults = data.items;
            this.decisionSearchTotal = data.total;
            this.decisionSearchTotalPages = Math.ceil(data.total / this.decisionSearchSize);
            this.searchDecisionsResults.forEach(d => {
              this.$set(this.expandedSearchDecisions, d.id, false);
            });
          });
      }
      // Signal logs
      if (this.searchEntityType === "signal_logs") {
        let url = `/ui/search_signal_logs?q=${qEnc}&page=${this.signalLogsSearchPage}&size=${this.signalLogsSearchSize}`;
        fetch(url)
          .then(r => r.json())
          .then(data => {
            this.searchSignalLogsResults = data.items;
            this.signalLogsSearchTotal = data.total;
            this.signalLogsSearchTotalPages = Math.ceil(data.total / this.signalLogsSearchSize);
            this.searchSignalLogsResults.forEach(log => {
              this.$set(this.expandedSearchSignalLogs, log.id, false);
              if (!log.param_values) {
                log.param_values = [];
              }
            });
          });
      }
    },
    // Tenants search pagination
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
    // Checkpoints search pagination
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
    // Signals search pagination
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
    // Decision search pagination
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
    // Signal logs search pagination
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
      fetch(`/ui/tenants/${tid}`, {
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
      fetch(`/ui/checkpoints/${cpId}`)
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
          return fetch(`/ui/checkpoints/${cpId}`, {
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
      fetch(`/ui/signals/${sid}`)
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
            bearer_token: original.bearer_token,
            allow_caching: original.allow_caching,
            global_reuse: original.global_reuse,
            function_params_template: original.function_params_template,
            makeCurrentVersion: this.makeCurrentVersion
          };
          return fetch(`/ui/signals/${sid}`, {
            method: "PUT",
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
      if (this.expandedSearchDecisions[did]) {
        // If we are expanding, fetch decision details if not already loaded
        if (!this.searchDecisionDetails[did]) {
          this.fetchDecisionDetails(did);
        }
      }
    },
    fetchDecisionDetails(decisionId) {
      fetch(`/decisions/${decisionId}`)
        .then(async r => {
          if (!r.ok) {
            const txt = await r.text();
            throw new Error("Failed to fetch decision details: " + txt);
          }
          return r.json();
        })
        .then(decisionData => {
          this.$set(this.searchDecisionDetails, decisionId, decisionData);
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
    //---------------------------------------
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
      fetch(url)
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
            this.$set(this.expandedTestDecCheckpoints, cp.id, false);
          });
        })
        .catch(err => console.error("Error searching test dec checkpoints:", err));
    },
    loadAllTestDecCheckpoints(page) {
      this.testDecCheckpointPage = page;
      let url = `/ui/checkpoints?page=${page}&size=${this.testDecCheckpointSize}`;
      fetch(url)
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
            this.$set(this.expandedTestDecCheckpoints, cp.id, false);
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
      fetch(url)
        .then(r => r.json())
        .then(data => {
          const signals = data.items || [];
          this.$set(this.testDecAssocSignals, cpId, signals);
          if (!this.expandedTestDecSignals[cpId]) {
            this.$set(this.expandedTestDecSignals, cpId, {});
          }
          signals.forEach(sig => {
            this.$set(this.expandedTestDecSignals[cpId], sig.id, false);
          });
          if (!this.testDecParams[cpId]) {
            this.$set(this.testDecParams, cpId, {});
          }
          signals.forEach(sig => {
            if (!this.testDecParams[cpId][sig.id]) {
              this.$set(this.testDecParams[cpId], sig.id, {});
              sig.param_placeholders.forEach(ph => {
                this.$set(this.testDecParams[cpId][sig.id], ph, "");
              });
            }
          });
        })
        .catch(err => console.error("Error loading checkpoint signals for test:", err));
    },
    toggleExpandTestDecSignal(cpId, sigId) {
      if (!this.expandedTestDecSignals[cpId]) {
        this.$set(this.expandedTestDecSignals, cpId, {});
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
        alert("Checkpoint not found in test list.");
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
        checkpoint_name: cp.name,
        applicant_id: applicantId,
        correlation_id: correlationId,
        parameters: paramMap
      };

      fetch("/decisions", {
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
          this.$set(this.testDecResponses, cpId, resp);
        })
        .catch(err => {
          console.error("Error invoking decision:", err);
          this.$set(this.testDecResponses, cpId, { error: err.message });
        });
    },

    //---------------------------------------
    // Helpers for DSL placeholders in UI
    //---------------------------------------
    generateDslPlaceholder(cpId) {
      // Gather the names of signals associated with this checkpoint:
      const cpData = this.checkpointEdits[cpId];
      if (!cpData || !cpData.associatedSignals) return "e.g. signalA and signalB";
      let signalNames = cpData.associatedSignals.map(s => s.name).filter(Boolean);
      let placeholderList = [];
      cpData.associatedSignals.forEach(sig => {
        if (sig.param_placeholders && sig.param_placeholders.length) {
          placeholderList = placeholderList.concat(sig.param_placeholders);
        }
      });
      signalNames = signalNames.map(n => n.trim()).filter(n => n.length > 0);
      placeholderList = placeholderList.map(p => p.trim()).filter(p => p.length > 0);

      if (!signalNames.length && !placeholderList.length) {
        return "e.g. signalA and signalB";
      }
      let exampleSignalPart = signalNames.join(" and ");
      if (!exampleSignalPart) exampleSignalPart = "signalA";
      let examplePlaceholderPart = placeholderList.join(", ");
      if (examplePlaceholderPart) {
        examplePlaceholderPart = ` (placeholders: ${examplePlaceholderPart})`;
      }
      return `Try something like: ${exampleSignalPart} > 0${examplePlaceholderPart}`;
    },
    generateDslTooltip(cpId) {
      const cpData = this.checkpointEdits[cpId];
      if (!cpData || !cpData.associatedSignals) return "DSL expression references signal names as variables";
      let signalNames = cpData.associatedSignals.map(s => s.name).filter(Boolean);
      let placeholderList = [];
      cpData.associatedSignals.forEach(sig => {
        if (sig.param_placeholders && sig.param_placeholders.length) {
          placeholderList = placeholderList.concat(sig.param_placeholders);
        }
      });
      signalNames = signalNames.map(n => n.trim()).filter(n => n.length > 0);
      placeholderList = placeholderList.map(p => p.trim()).filter(p => p.length > 0);
      const signalsStr = signalNames.length ? "Signals: " + signalNames.join(", ") : "No signals.";
      const placeholdersStr = placeholderList.length
        ? " | Placeholders: " + placeholderList.join(", ")
        : "";
      return `DSL references these signals: ${signalsStr}${placeholdersStr}`;
    },
    fetchCheckpoints(page) {
      const url = new URL('/ui/checkpoints', window.location.origin);
      url.searchParams.set('page', page);
      url.searchParams.set('size', this.checkpointSize);
      if (this.checkpointsTenantFilter) {
        url.searchParams.set('tenant_id', this.checkpointsTenantFilter);
      }
      
      fetch(url)
        .then(response => response.json())
        .then(data => {
          this.checkpoints = data.items;
          this.checkpointTotal = data.total;
          this.checkpointTotalPages = data.total_pages;
          this.checkpointPage = data.page;
        })
        .catch(error => {
          console.error('Error fetching checkpoints:', error);
        });
    },
    setAsCurrentVersion(checkpointId) {
      const checkpoint = this.checkpoints.find(cp => cp.id === checkpointId);
      if (!checkpoint) return;

      const payload = {
        tenant_id: checkpoint.tenant_id,
        name: checkpoint.name,
        checkpoint_id: checkpointId
      };

      fetch(`/ui/checkpoints/${checkpointId}/make_current`, {
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
      .then(() => {
        // Refresh the checkpoints list to show updated version status
        this.loadAllCheckpoints(this.checkpointPage);
      })
      .catch(error => {
        console.error('Error setting current version:', error);
        alert('Error setting current version: ' + error.message);
      });
    },
    renderSignalDetails(signal) {
      return `
        <div class="signal-details">
          <div class="detail-section">
            <h4>Basic Information</h4>
            <table class="detail-table">
              <tr>
                <td class="label">Type:</td>
                <td>${signal.type}</td>
              </tr>
              <tr>
                <td class="label">Method of Call:</td>
                <td>${signal.method_of_call || 'N/A'}</td>
              </tr>
              <tr>
                <td class="label">Cost:</td>
                <td>${signal.cost}</td>
              </tr>
            </table>
          </div>

          ${signal.type === 'http' ? `
            <div class="detail-section">
              <h4>HTTP Endpoint Details</h4>
              <table class="detail-table">
                <tr>
                  <td class="label">HTTP Method:</td>
                  <td>${signal.http_method}</td>
                </tr>
                <tr>
                  <td class="label">URL Parameters Template:</td>
                  <td><pre>${signal.request_url_params_template || 'N/A'}</pre></td>
                </tr>
                <tr>
                  <td class="label">Body Template:</td>
                  <td><pre>${signal.request_body_template || 'N/A'}</pre></td>
                </tr>
                <tr>
                  <td class="label">Headers Template:</td>
                  <td><pre>${signal.request_headers_template || 'N/A'}</pre></td>
                </tr>
              </table>
            </div>
          ` : ''}

          ${signal.type === 'function' ? `
            <div class="detail-section">
              <h4>Function Details</h4>
              <table class="detail-table">
                <tr>
                  <td class="label">Expression Body:</td>
                  <td><pre>${signal.expression_body || 'N/A'}</pre></td>
                </tr>
                <tr>
                  <td class="label">Function Parameters:</td>
                  <td><pre>${signal.function_params_template || 'N/A'}</pre></td>
                </tr>
              </table>
            </div>
          ` : ''}

          <div class="detail-section">
            <h4>Parameters</h4>
            <table class="detail-table">
              <tr>
                <td class="label">Parameter Placeholders:</td>
                <td>
                  ${signal.param_placeholders && signal.param_placeholders.length ? `
                    <ul class="param-list">
                      ${signal.param_placeholders.map(param => `<li>${param}</li>`).join('')}
                    </ul>
                  ` : 'No parameters required'}
                </td>
              </tr>
            </table>
          </div>

          <div class="detail-section">
            <h4>Additional Settings</h4>
            <table class="detail-table">
              <tr>
                <td class="label">Cache Expiration:</td>
                <td>${signal.cache_expiration_seconds} seconds</td>
              </tr>
              <tr>
                <td class="label">Timeout:</td>
                <td>${signal.timeout_seconds} seconds</td>
              </tr>
              <tr>
                <td class="label">Can Run in Parallel:</td>
                <td>${signal.can_run_in_parallel ? 'Yes' : 'No'}</td>
              </tr>
              <tr>
                <td class="label">Order of Evaluation:</td>
                <td>${signal.order_of_evaluation}</td>
              </tr>
              <tr>
                <td class="label">Allow Caching:</td>
                <td>${signal.allow_caching ? 'Yes' : 'No'}</td>
              </tr>
              <tr>
                <td class="label">Global Reuse:</td>
                <td>${signal.global_reuse ? 'Yes' : 'No'}</td>
              </tr>
            </table>
          </div>
        </div>
      `;
    },
    saveCheckpoint(id) {
      const checkpoint = this.checkpointEdits[id];
      const payload = {
        tenant_id: this.checkpointsTenantFilter,
        name: checkpoint.name,
        description: checkpoint.description,
        type: checkpoint.type,
        dsl_expression: checkpoint.dsl_expression,
        makeCurrentVersion: checkpoint.makeCurrentVersion
      };

      fetch(`/ui/checkpoints/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(r => r.json())
        .then(() => {
          this.expandedCheckpoints[id] = false;
          this.loadAllCheckpoints(this.checkpointPage);
        })
        .catch(err => {
          console.error("Error saving checkpoint:", err);
        });
    },
    // Add after loadAllSignals method
    onSignalPageChange(page) {
      if (this.signalSearchTerm && this.signalSearchTerm.trim()) {
        this.searchSignals(this.signalSearchTerm, page);
      } else {
        this.loadAllSignals(page);
      }
    },
    onSearchSignalPageChange(page) {
      this.signalSearchPage = page;
      const qEnc = encodeURIComponent(this.searchQuery);
      let url = `/ui/search_signals?q=${qEnc}&page=${page}&size=${this.signalSearchSize}`;
      if (this.signalsActiveFilter === 'active') {
        url += '&active_only=true';
      }
      fetch(url)
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
    onCheckpointSignalPageChange(page) {
      if (this.newCheckpointData.signalSearch && this.newCheckpointData.signalSearch.trim()) {
        this.fetchCheckpointSignalSearch(page);
      } else {
        this.loadAllSignalsForCheckpoint(page);
      }
    },

    //---------------------------------------
    // GLOBAL TENANT MANAGEMENT
    //---------------------------------------
    getCurrentTenant() {
      return this.currentGlobalTenant;
    },
    setCurrentTenant(tenant) {
      this.currentGlobalTenant = tenant;
      // Update the tenant filter in all relevant views
      this.checkpointsTenantFilter = tenant ? tenant.id : "";
      this.signalsTenantFilter = tenant ? tenant.id : "";
      this.assocTenantFilter = tenant ? tenant.id : "";
      this.testDecTenantFilter = tenant ? tenant.id : "";
    },
    setAsCurrentVersion(signalId) {
      if (!this.currentGlobalTenant) {
        alert("Please select a tenant first.");
        return;
      }

      const signal = this.signals.find(s => s.id === signalId);
      if (!signal) return;

      fetch(`/ui/signals/${signalId}/toggle_active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        // Refresh the signals list to show updated version status
        this.loadAllSignals(this.signalPage);
      })
      .catch(error => {
        console.error('Error setting current version:', error);
        alert('Error setting current version: ' + error.message);
      });
    },
  },
  mounted() {
    this.fetchAllTenants();
    this.fetchCheckpoints(1);
    this.isVueReady = true;
  },
  watch: {
    checkpointsTenantFilter(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.loadAllCheckpoints(1);
      }
    },
    checkpointsActiveFilter(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.loadAllCheckpoints(1);
      }
    },
    signalsActiveFilter(newVal, oldVal) {
      if (newVal !== oldVal) {
        if (this.signalSearchTerm) {
          this.searchSignals(this.signalSearchTerm, 1);
        } else {
          this.loadAllSignals(1);
        }
      }
    }
  }
});