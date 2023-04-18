<script lang='ts'>
  import type { Thread } from '$lib/types.svelte';
  import { ListBox, ListBoxItem } from '@skeletonlabs/skeleton';
  export let activeThreadId: string; // the UUID of the active thread
  export let availableThreads: Map<string, Thread>;
  // Sort Threads by date youngest to oldest
  let threadStack: Thread[] = [];
  availableThreads.forEach((value: Thread) => {
    threadStack.push(value);
  });
  threadStack.sort((a: Thread, b: Thread) => {
    return b.created.getTime() - a.created.getTime();
  });
  // Pop the active thread & push it to the top of the stack
  let activeThreadIndex = threadStack.findIndex((thread: Thread) => {
    return thread.id === activeThreadId;
  });
  let activeThreadObj = threadStack.splice(activeThreadIndex, 1)[0];
  threadStack.push(activeThreadObj);
  console.log(threadStack);

  const selectThread = (index: number) => {
    console.log("selectThread: ", index);
    activeThreadId = threadStack[index].id;
  };
</script>

<div class="chat-thread-sidebar">
  <ListBox>
    {#each threadStack as thread, index}
    <ListBoxItem 
      bind:group={activeThreadId}
      name="thread"
      value={thread.id} on:click={
          () => selectThread(index)
      } on:keydown={
        (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            selectThread(index);
          }
        }
      } tabindex="0">{thread.title}</ListBoxItem>
    {/each}
  </ListBox>
</div>

<style>
  .chat-thread-sidebar {
    background: grey;
  }

  .thread {
    background: lightcoral;
  }

  .thread p {
    margin: 0;
  }

  .timestamp {
    font-size: 0.8em;
  }

  .active {
    background-color: lightblue;
  }
</style>
