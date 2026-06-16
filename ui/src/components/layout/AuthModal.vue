<template>
  <div class="modal-overlay">
    <div class="modal-content card">
      <h3>Local Demo Admin Login</h3>
      <p class="text-muted">
        Enter the admin bearer token from your local <code>.env.local</code>
        (generate with <code>bash scripts/create_demo_env.sh</code>).
      </p>
      <div class="form-field">
        <label>Admin bearer token</label>
        <input
          type="password"
          v-model="$root.authTokenInput"
          placeholder="Paste admin token"
          @keyup.enter="$root.submitAuthToken()"
        />
      </div>
      <p v-if="$root.authError" class="text-danger">{{ $root.authError }}</p>
      <div class="form-actions">
        <button class="btn-primary" type="button" @click="$root.submitAuthToken()">
          Continue
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: "AuthModal" };
</script>
