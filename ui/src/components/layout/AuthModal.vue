<template>
  <div class="modal-overlay">
    <div class="modal-content card">
      <h3>{{ showDevDemoUi ? "Development sign-in" : "Sign in" }}</h3>
      <p v-if="showDevDemoUi" class="text-muted">
        Enter the admin bearer token from your local <code>.env.local</code>
        (generate with <code>bash scripts/create_demo_env.sh</code>).
      </p>
      <p v-else class="text-muted">Enter your admin bearer token to continue.</p>
      <div class="form-field">
        <label for="auth-token">Admin bearer token</label>
        <input
          id="auth-token"
          v-model="tokenInput"
          type="password"
          placeholder="Paste admin token"
          @keyup.enter="submit"
        />
      </div>
      <p v-if="authError" class="text-danger">{{ authError }}</p>
      <div class="form-actions">
        <button class="btn-primary" type="button" @click="submit">Continue</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { SHOW_DEV_DEMO_UI } from "@/app/config";
import { useAuthStore } from "@/stores/authStore";

const auth = useAuthStore();
const { tokenInput, authError } = storeToRefs(auth);
const showDevDemoUi = SHOW_DEV_DEMO_UI;

function submit() {
  void auth.submitToken();
}
</script>
