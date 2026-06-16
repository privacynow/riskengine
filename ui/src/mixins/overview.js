import api from "../api/client.js";
import { notify } from "../stores/notices.js";
import { setStoredAdminToken } from "../api/auth.js";


export default {
  data: function () {
    return {
      dashboardLoading: false,
      dashboardError: "",
      dashboardStats: {
        tenantCount: 0,
        checkpointCount: 0,
        signalCount: 0,
        recentDecisions: [],
        failedSignalLogs: [],
      },
    };
  },
  methods: {
    loadDashboard: function () {
      var self = this;
      self.dashboardLoading = true;
      self.dashboardError = "";
      var tenantId =
        self.currentGlobalTenant && self.currentGlobalTenant.id
          ? self.currentGlobalTenant.id
          : null;

      var tenantReq = api.tenants.list(1, 1);
      var checkpointReq = tenantId
        ? api.checkpoints.list({
            page: 1,
            size: 1,
            tenant_id: tenantId,
            active_only: true,
          })
        : Promise.resolve({ total: 0, items: [] });
      var signalReq = tenantId
        ? api.signals.list({
            page: 1,
            size: 1,
            tenant_id: tenantId,
            active_only: true,
          })
        : Promise.resolve({ total: 0, items: [] });
      var decisionsReq = api.decisions.search({
        page: 1,
        size: 5,
      });
      var failedLogsReq = api.signalLogs.search({
        q: "false",
        page: 1,
        size: 5,
      });

      Promise.all([
        tenantReq,
        checkpointReq,
        signalReq,
        decisionsReq,
        failedLogsReq,
      ])
        .then(function (results) {
          self.dashboardStats.tenantCount = results[0].total || 0;
          self.dashboardStats.checkpointCount = results[1].total || 0;
          self.dashboardStats.signalCount = results[2].total || 0;
          self.dashboardStats.recentDecisions = results[3].items || [];
          self.dashboardStats.failedSignalLogs = (results[4].items || []).filter(
            function (row) {
              return row.success === false;
            }
          );
        })
        .catch(function (err) {
          self.dashboardError = err.message || "Failed to load dashboard.";
        })
        .finally(function () {
          self.dashboardLoading = false;
        });
    },
  },
};
