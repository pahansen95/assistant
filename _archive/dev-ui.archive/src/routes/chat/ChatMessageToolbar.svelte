<div class="container">
  <textarea
    class="textbox"
    bind:value={message}
    on:keydown={(e) => e.key === "Enter" && sendMessage()}
  />
  <button class="button" on:click={sendMessage}>Send</button>
</div>

<script>
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let message = "";

  function sendMessage() {
    if (message.trim()) {
      dispatch("send", message);
      message = "";
    }
  }
</script>

<style>
  .container {
    display: flex;
    align-items: center;
    padding: 0.5rem;
    width: 100%; /* fill parent width */
    height: 100%; /* fill parent height */
    resize: none;
    background-color: blueviolet;
  }

  .textbox {
    flex: 1;
    margin-right: 0.5rem;
    border: 1px solid gray;
    border-radius: 0.25rem;
    padding: 0.25rem;
    resize: none;
  }

  .button {
    background-color: blue;
    color: white;
    border: none;
    border-radius: 0.25rem;
    padding: 0.5rem;
    cursor: pointer;
  }
</style>
