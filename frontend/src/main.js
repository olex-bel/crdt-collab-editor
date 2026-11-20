import Quill from 'quill'
import QuillCursors from 'quill-cursors'
import * as Y from 'yjs'
import { QuillBinding } from 'y-quill'
import { WebsocketProvider } from 'y-websocket'
import 'quill/dist/quill.core.css'
import 'quill/dist/quill.snow.css'

export function buildDocumentWsUrl() {
  const rawBase = (import.meta.env.VITE_BACKEND_URL)?.trim();
  const cleanBase = rawBase.replace(/\/+$/, "");

  const wsBase = cleanBase.startsWith("https://")
    ? "wss://" + cleanBase.slice("https://".length)
    : cleanBase.startsWith("http://")
      ? "ws://" + cleanBase.slice("http://".length)
      : cleanBase;

  return `${wsBase}/ws/documents`;
}

Quill.register('modules/cursors', QuillCursors);

const docId = window.location.pathname.split('/').pop() || 'default-document';
const ydoc = new Y.Doc();
const url = buildDocumentWsUrl();

console.log('Connecting to document:', docId, 'via', url);

const quill = new Quill(document.querySelector('#editor'), {
  modules: {
    cursors: true,
    toolbar: [
      [{ header: [1, 2, false] }],
      ['bold', 'italic', 'underline'],
      ['image', 'code-block']
    ],
    history: {
      userOnly: true
    }
  },
  placeholder: 'Start collaborating...',
  theme: 'snow'
})

const provider = new WebsocketProvider(
  url,
  docId,
  ydoc
)

const ytext = ydoc.getText('quill')
const binding = new QuillBinding(ytext, quill, provider.awareness)

provider.on('sync', (isSynced) => {
  if (isSynced) {
    const meta = ydoc.getMap('meta')
    console.log('Document loaded:', meta.get('title'))
  }
})