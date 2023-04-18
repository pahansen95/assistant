<script lang="ts">
  import type { Message, Thread } from '$lib/types.svelte';
  import {v4 as uuidv4} from 'uuid';

  import ChatTranscriptWindow from './ChatTranscriptWindow.svelte';
  import ChatThreadSidebar from './ChatThreadSidebar.svelte';
  import ChatMessageToolbar from './ChatMessageToolbar.svelte';

  let sidebar: HTMLDivElement;
  let transcript: HTMLDivElement;
  let toolbar: HTMLDivElement;

  // let availableThreads: string[] = ["Thread 1", "Thread 2", "Thread 3"];
  let availableThreads: Map<string, Thread> = new Map();
  // TODO Load thread data
  
  // if no thread data then create an empy thread
  if (availableThreads.size === 0) {
    let thread_id: string = uuidv4();
    availableThreads.set(
      thread_id,
      {
        "id": thread_id,
        "title": "New Thread",
        "created": new Date()
      }
    );
  }
  // For now add in some dummy data. loop over a range adding threads
  for (let i = 0; i < 3; i++) {
    let thread_id: string = uuidv4();
    availableThreads.set(
      thread_id,
      {
        "id": thread_id,
        "title": "Thread " + (i + 1),
        "created": new Date()
      }
    );
  }
 

  // Get the youngest thread
  let activeThread: Thread = availableThreads.values().next().value;
  console.log("thread @ index 0: ", activeThread);
  availableThreads.forEach((value: Thread) => {
    if (value.created > activeThread.created) {
      activeThread = value;
    }
  });
  console.log("youngest thread: ", activeThread);

  // Get the current thread's messages
  let threadMessages: Map<string, Message[]> = new Map();
  if (activeThread.title === "New Thread") {
    // Add dummy data for now
    threadMessages.set(activeThread.id, [
      {
        "content": "Message 1",
        "created": new Date()
      },
      {
        "content": "Message 2",
        "created": new Date()
      }
    ]);
  } else {
    // TODO: Load the message data for an existing thread
    throw new Error("Loading messages for an existing thread is not implemented");
  }
  let activeThreadMessages = threadMessages.get(activeThread.id);
  console.log("activeThreadMessages: ", activeThreadMessages)
  
  const handleSubmit = (content: string) => {
    throw new Error("Submitting a message is not implemented");
  };
</script>

<div class="container">
  <div class="sidebar" bind:this={sidebar}>
    <ChatThreadSidebar availableThreads={availableThreads} activeThreadId={activeThread.id} />
  </div>
  <div class="viewport">
    <div class="transcript" bind:this={transcript}>
      <ChatTranscriptWindow messageThread={activeThreadMessages} />
    </div>
    <div class="toolbar" bind:this={toolbar}>
      <ChatMessageToolbar />
    </div>
  </div>
</div>

<style>
  .container {
    display: flex;
    height: 100vh;
    width: 100vw;
    padding: 0;
    background-color: black;
  }
  .sidebar {
    width: var(--sidebar-width, 20%);
    min-width: 20%;
    max-width: 50%;
    background-color: darkred;
    resize: horizontal;
    overflow: auto;
  }
  .viewport {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: darkblue;
  }
  .transcript {
    height: var(--transcript-height, 80%);
    background-color: darkgreen;
    overflow-y: auto;
  }
  .toolbar {
    height: var(--toolbar-height, 20%);
    background-color: darkgreen;
    resize: vertical;
    overflow: auto;
    position: sticky;
    bottom: 0;
    min-height: 20%;
  }
</style>
