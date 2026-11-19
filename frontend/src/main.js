import Quill from 'quill'
import QuillCursors from 'quill-cursors'
import * as Y from 'yjs'
import { QuillBinding } from 'y-quill'
import { WebsocketProvider } from 'y-websocket'
import 'quill/dist/quill.core.css'
import 'quill/dist/quill.snow.css'

Quill.register('modules/cursors', QuillCursors)

const docId = window.location.pathname.split('/').pop() || 'default-document'
const ydoc = new Y.Doc()
const url = `ws://${import.meta.env.VITE_BACKEND_HOST}:${import.meta.env.VITE_BACKEND_PORT}/ws/documents`

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