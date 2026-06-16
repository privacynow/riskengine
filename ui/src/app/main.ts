import { createApp } from "vue";
import App from "@/App.vue";
import pinia from "@/app/pinia";
import router from "@/app/router";

import "@/styles/tokens.css";
import "@/styles/base.css";
import "@/styles/layout.css";
import "@/styles/components.css";
import "@/styles/forms.css";
import "@/styles/tables.css";
import "@/styles/workbench.css";
import "@/styles/shell.css";

const app = createApp(App);
app.use(pinia);
app.use(router);
app.mount("#app");
