<script lang="ts">
  import { link } from "svelte-spa-router";
  import QuestionList from "../components/QuestionList.svelte";
  import ErrorAlert from "../components/ErrorAlert.svelte";
  import { session } from "../lib/stores";
</script>

<svelte:head><title>CAP - Dashboard</title></svelte:head>

{#if $session.status === "loading"}
  <div class="spin-center" role="status" aria-live="polite">
    <i class="fa-solid fa-circle-notch fa-spin fa-2x me-2"></i>
    <span>Loading session...</span>
  </div>
{:else if $session.status === "error"}
  <ErrorAlert
    title="Could not load session"
    message={$session.message}
  />
{:else}
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h2 class="h4 mb-0">Dashboard</h2>
    {#if $session.status === "ready" && $session.user.projects.length > 0}
      <a class="btn btn-primary" href="/question/new" use:link>
        <i class="fa-solid fa-circle-plus me-1"></i>New question
      </a>
    {/if}
  </div>
  <QuestionList
    user={$session.status === "ready" ? $session.user : null}
  />
{/if}
