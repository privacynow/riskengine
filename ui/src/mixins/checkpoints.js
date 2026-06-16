import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    checkpointsActiveFilter: "all",
    checkpointSearchTerm: "",
    showCheckpointCreateForm: false,
    makeNewVersionCurrent: false,
    makeCurrentVersion: false,
    existingCheckpoint: null,
    showCheckpointConfirmation: false,
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
    checkpointSignalSearch: {},
    checkpointSignalCandidates: {},
    checkpointSignalCandidatePage: {},
    checkpointSignalCandidateSize: 5,
    checkpointSignalCandidateTotal: {},
    checkpointSignalCandidateTotalPages: {},
    expandedCheckpointCandidate: {},
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
    }
    };
  },
  methods: {
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
        
      api.request(url)
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
            this.checkpointEdits[cp.id] = {
              name: cp.name,
                description: cp.description || '',
                type: cp.type || '',
                dsl_expression: cp.dsl_expression || '',
                makeCurrentVersion: false
              };
              this.expandedCheckpoints[cp.id] = false;
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

      api.request(url)
        .then(r => r.json())
        .then(data => {
          this.checkpoints = data.items;
          this.checkpointTotal = data.total;
          this.checkpointTotalPages = Math.ceil(data.total / this.checkpointSize);
          this.checkpoints.forEach(cp => {
            this.expandedCheckpoints[cp.id] = false;
            this.checkpointEdits[cp.id] = {
              name: cp.name,
              description: cp.description,
              type: cp.type,
              dsl_expression: cp.dsl_expression,
              method_of_call: cp.method_of_call,
              max_cost: cp.max_cost,
              override_cost_flag: cp.override_cost_flag,
              timeout_seconds: cp.timeout_seconds,
              associatedSignals: []
            };
            this.checkpointSignalSearch[cp.id] = "";
            this.checkpointSignalCandidates[cp.id] = [];
            this.checkpointSignalCandidatePage[cp.id] = 1;
            this.checkpointSignalCandidateTotal[cp.id] = 0;
            this.checkpointSignalCandidateTotalPages[cp.id] = 1;
            this.expandedCheckpointCandidate[cp.id] = {};
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
      api.request(`/ui/signals?checkpoint_id=${cpId}&page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const items = data.items || [];
          this.checkpointEdits[cpId].associatedSignals = items;
        })
        .catch(err => console.error(`Error fetching signals for checkpoint ${cpId}`, err));
    },

    removeSignalAssociation(cpId, sigId) {
      // We'll fetch all checkpoint_signals then remove
      api.request(`/ui/checkpoint_signals?page=1&size=9999`)
        .then(r => r.json())
        .then(data => {
          const assoc = data.items.find(a => a.checkpoint_id === cpId && a.signal_id === sigId);
          if (!assoc) {
            notify( { message: "Association not found. Possibly already removed.", isError: true });
            return;
          }
          return api.request(`/ui/checkpoint_signals/${assoc.id}`, { method: "DELETE" });
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

      api.request(`/ui/checkpoints/${cpId}`, {
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
        this.checkpointEdits[cpId] = {
          name: checkpoint.name,
          description: checkpoint.description,
          type: checkpoint.type,
          dsl_expression: checkpoint.dsl_expression,
          method_of_call: checkpoint.method_of_call,
          max_cost: checkpoint.max_cost,
          override_cost_flag: checkpoint.override_cost_flag,
          timeout_seconds: checkpoint.timeout_seconds,
          associatedSignals: []
        };
          this.expandedCheckpoints[cpId] = false;
        this.makeCurrentVersion = false;
          this.loadAllCheckpoints(this.checkpointPage);
        })
      .catch(error => {
        console.error('Error saving checkpoint:', error);
        notify( { message: 'Error saving checkpoint: ' + error.message, isError: true });
      });
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

      api.request(`/ui/checkpoints/${id}`, {
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
    // Add after loadAllSignals method,

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
      const tenantId = this.activeTenantId();
      // Validate required fields
      if (!tenantId) {
        notify( { message: "Please select a tenant first.", isError: true });
        return;
      }
      if (!this.newCheckpointData.name) {
        notify( { message: "Checkpoint name is required.", isError: true });
        return;
      }
      if (!this.newCheckpointData.type) {
        notify( { message: "Checkpoint type is required.", isError: true });
        return;
      }
      if (!this.newCheckpointData.dsl_expression) {
        notify( { message: "DSL expression is required.", isError: true });
        return;
      }

      const payload = {
        tenant_id: tenantId,
        name: this.newCheckpointData.name,
        description: this.newCheckpointData.description || "",
        type: this.newCheckpointData.type,
        dsl_expression: this.newCheckpointData.dsl_expression,
        makeCurrentVersion: this.newCheckpointData.makeCurrentVersion,
        signals: (this.newCheckpointData.associatedSignals || []).map(s => s.id)
      };

      // First check if a checkpoint with this name already exists
      const url = `/ui/search_checkpoints?q=${encodeURIComponent(this.newCheckpointData.name)}&tenant_id=${tenantId}&page=1&size=1`;
      
      api.request(url)
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
          
          return api.request("/ui/checkpoints", {
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
          notify( { message: 'Error creating checkpoint: ' + err.message, isError: true });
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
      
      api.request("/ui/checkpoints", {
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
          notify( { message: 'Error creating checkpoint: ' + err.message, isError: true });
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
        notify( { message: "No checkpoint ID found. Create checkpoint first.", isError: true });
        return;
      }
      const payload = {
        checkpoint_id: this.createdCheckpointId,
        signal_id: signalId
      };
      api.request("/ui/checkpoint_signals", {
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
          notify( { message: "Signal associated!", isError: false });
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
      api.request(url)
        .then(r => r.json())
        .then(data => {
          this.checkpointSignalCandidates[cpId] = data.items || [];
          this.checkpointSignalCandidateTotal[cpId] = data.total;
          this.checkpointSignalCandidateTotalPages[cpId] = Math.ceil(data.total / this.checkpointSignalCandidateSize);
          this.checkpointSignalCandidates[cpId].forEach(s => {
            if (!this.expandedCheckpointCandidate[cpId]) {
              this.expandedCheckpointCandidate[cpId] = {};
            }
            this.expandedCheckpointCandidate[cpId][s.id] = false;
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
      api.request(url)
        .then(r => r.json())
        .then(data => {
          this.checkpointSignalCandidates[cpId] = data.items || [];
          this.checkpointSignalCandidateTotal[cpId] = data.total;
          this.checkpointSignalCandidateTotalPages[cpId] = Math.ceil(data.total / this.checkpointSignalCandidateSize);
          this.checkpointSignalCandidates[cpId].forEach(s => {
            if (!this.expandedCheckpointCandidate[cpId]) {
              this.expandedCheckpointCandidate[cpId] = {};
            }
            this.expandedCheckpointCandidate[cpId][s.id] = false;
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
      api.request("/ui/checkpoint_signals", {
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
    //---------------------------------------,

    onCheckpointSignalPageChange(page) {
      if (this.newCheckpointData.signalSearch && this.newCheckpointData.signalSearch.trim()) {
        this.fetchCheckpointSignalSearch(page);
      } else {
        this.loadAllSignalsForCheckpoint(page);
      }
    },

    setCheckpointCurrentVersion(checkpointId) {
      const checkpoint = this.checkpoints.find(cp => cp.id === checkpointId);
      if (!checkpoint) return;

      const payload = {
        tenant_id: checkpoint.tenant_id,
        name: checkpoint.name,
        checkpoint_id: checkpointId
      };

      api.request(`/ui/checkpoints/${checkpointId}/make_current`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(response => {
          if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
          }
          return response.json();
        })
        .then(() => {
          this.loadAllCheckpoints(this.checkpointPage);
        })
        .catch(error => {
          console.error("Error setting current version:", error);
          notify( {
            message: "Error setting current version: " + error.message,
            isError: true
          });
        });
    },

    //---------------------------------------
    // GLOBAL TENANT MANAGEMENT
    //---------------------------------------
  }
};
