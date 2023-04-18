<script lang='ts'>
  import type { Message } from '$lib/types.svelte';
  export let messageThread: Message[];
  console.log(messageThread);
</script>

<!-- <h1>Chat Transcript Window</h1> -->
<div class="transcript-window">
  {#each messageThread as message}
    <div class="message">
      <div class="message-created">{message.created.toLocaleTimeString()} - {message.created.toDateString()}</div>
      <div class="message-content">{message.content}</div>
    </div>
  {/each}
</div>

<style>
  .transcript-window {
    background-color: blue;
    overflow-y: scroll;
    padding: 1rem;
  }

  .message {
    margin-bottom: 1rem;
    background-color: lightblue;
  }
</style>

