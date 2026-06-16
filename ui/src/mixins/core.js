import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    view: "overview",
    isVueReady: false,
    showAuthPrompt: true,
    authTokenInput: "",
    authError: "",
    showSignalConfirmation: false,
    isCurrentVersion: function(checkpoint) {
      return checkpoint && checkpoint.is_current_version === true;
    },
    currentGlobalTenant: null,
    allTenants: [],
    checkpointsTenantFilter: "",
    signalsTenantFilter: "",
    assocTenantFilter: "",
    testDecTenantFilter: ""
    };
  },
  methods: {
    activeTenantId() {
      if (this.checkpointsTenantFilter) {
        return this.checkpointsTenantFilter;
      }
      if (this.currentGlobalTenant && this.currentGlobalTenant.id) {
        return this.currentGlobalTenant.id;
      }
      return "";
    },
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
      if (newView === "overview") {
        this.fetchAllTenants();
        this.loadDashboard();
      } else if (newView === "tenants") {
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
      } else if (newView === "test") {
        this.fetchAllTenants();
        this.testDecCheckpoints = [];
      } else if (newView === "audit") {
        this.fetchAllTenants();
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
    //---------------------------------------,

    fetchAllTenants() {
      api.request("/ui/tenants?page=1&size=9999")
        .then(r => r.json())
        .then(data => {
          this.allTenants = data.items || [];
        })
        .catch(err => console.error("Error fetching allTenants:", err));
    },

    //---------------------------------------
    // TENANTS
    //---------------------------------------,

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
      
      api.request(url)
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

    bootstrapApp() {
      this.showAuthPrompt = false;
      this.fetchAllTenants();
      this.isVueReady = true;
      this.switchView("overview");
    },

    submitAuthToken() {
      const token = this.authTokenInput.trim();
      if (!token) {
        this.authError = "Enter a bearer token.";
        return;
      }
      setStoredAdminToken(token);
      this.authError = "";
      api.request("/ui/tenants?page=1&size=1")
        .then(async (response) => {
          if (!response.ok) {
            const text = await response.text();
            throw new Error(text || "Admin token rejected.");
          }
          this.showAuthPrompt = false;
          this.bootstrapApp();
        })
        .catch((err) => {
          console.error(err);
          setStoredAdminToken("");
          this.authError = "Admin token rejected. Use the token from your local .env.local.";
          this.showAuthPrompt = true;
        });
    },

    clearAuthToken() {
      setStoredAdminToken("");
      this.authTokenInput = "";
      this.showAuthPrompt = true;
      this.isVueReady = false;
    }
  }
};
