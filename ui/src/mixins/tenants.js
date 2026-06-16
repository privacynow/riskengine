import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data() {
    return {
    tenantSearchTerm: "",
    newTenantName: "",
    showTenantCreateForm: false,
    copyFromTenantId: "",
    tenants: [],
    tenantPage: 1,
    tenantSize: 5,
    tenantTotal: 0,
    tenantTotalPages: 1,
    expandedTenants: {},
    tenantEdits: {}
    };
  },
  methods: {
    toggleTenantCreateForm() {
      this.showTenantCreateForm = !this.showTenantCreateForm;
    },

    fetchTenants(page) {
      this.tenantPage = page;
      const url = `/ui/tenants?page=${page}&size=${this.tenantSize}`;
      api.request(url)
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
      api.request(url)
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
      api.request("/ui/tenants", {
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
          notify( { message: 'Error creating tenant: ' + err.message, isError: true });
        });
    },

    toggleExpandTenant(tenantId) {
      this.expandedTenants[tenantId] = !this.expandedTenants[tenantId];
      if (this.expandedTenants[tenantId] && !this.tenantEdits[tenantId]) {
        const tenant = this.tenants.find(t => t.id === tenantId);
        if (tenant) {
          this.tenantEdits[tenantId] = { name: tenant.name };
        }
      }
    },

    saveTenant(tenantId) {
      if (!this.tenantEdits[tenantId]) return;
      
      const payload = {
        name: this.tenantEdits[tenantId].name,
        copyFromTenantId: this.copyFromTenantId
      };

      api.request(`/ui/tenants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          notify( { message: data.error, isError: true });
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
  }
};
