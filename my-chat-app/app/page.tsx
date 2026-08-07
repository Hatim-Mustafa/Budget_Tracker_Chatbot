"use client";

import { ChatBox, ChatConversationList } from '@mui/x-chat';
import { useChat, type ChatAdapter, type ChatUser } from '@mui/x-chat/headless';
import { forwardRef, useEffect, useSyncExternalStore, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Tooltip,
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import AddCommentIcon from '@mui/icons-material/AddComment';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import ChartRenderer, { type VisualizationSpec } from './components/ChartRenderer';
import { authFetch, isAuthenticated, logout } from './lib/auth';

const adapter: ChatAdapter = {
  async sendMessage({ message, conversationId, signal }) {
    const res = await authFetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role: 'user',
        content: message.parts.find(p => p.type === 'text')?.text ?? '',
        conversation_id: conversationId,
      }),
      signal,
    });
    const data: {
      message: string;
      conversation_id: string;
      visualizations: VisualizationSpec[];
    } = await res.json();

    return new ReadableStream({
      start(controller) {
        const id = crypto.randomUUID();
        controller.enqueue({ type: 'start', messageId: id });
        controller.enqueue({ type: 'text-start', id: 'text-1' });
        controller.enqueue({ type: 'text-delta', id: 'text-1', delta: data.message });
        controller.enqueue({ type: 'text-end', id: 'text-1' });
        if (data.visualizations.length > 0) {
          controller.enqueue({
            type: 'data-visualization',
            id: 'visualizations-1',
            data: data.visualizations,
          });
        }
        controller.enqueue({ type: 'finish', messageId: id });
        controller.close();
      },
    });
  },

  async listMessages({ conversationId }) {
    const res = await authFetch(`/conversations/${conversationId}/messages`);
    const data: {
      id: string;
      role: string;
      content: string;
      conversation_id: string;
      created_at: string | null;
    }[] = await res.json();

    return {
      messages: data
        .filter((m) => m.role === 'user' || m.role === 'assistant' || m.role === 'system')
        .map((m) => ({
          id: m.id,
          conversationId: m.conversation_id,
          role: m.role as 'user' | 'assistant' | 'system',
          createdAt: m.created_at ?? undefined,
          parts: [{ type: 'text' as const, text: m.content, state: 'done' as const }],
        })),
      hasMore: false,
    };
  },
};

const members = [
  { id: 'user-1', displayName: 'You', role: 'user' as const },
  { id: 'assistant-1', displayName: 'Assistant', role: 'assistant' as const },
];

type Conversation = {
  id: string;
  title?: string;
  participants?: ChatUser[];
};

/**
 * Subscribe to the auth token in localStorage. A no-op is fine: auth changes
 * always navigate (login -> /, logout -> /login), so this page never observes
 * a token change while mounted. The server snapshot stays `false` so SSR and
 * hydration stay consistent; the real token is only read after hydration.
 */
const subscribeAuth = () => () => {};

export default function App() {
  const router = useRouter();
  const authChecked = useSyncExternalStore(subscribeAuth, isAuthenticated, () => false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [renameConversationId, setRenameConversationId] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newTitleDraft, setNewTitleDraft] = useState('');

  useEffect(() => {
    if (!authChecked) {
      router.replace('/login');
    }
  }, [authChecked, router]);

  useEffect(() => {
    if (!authChecked) return;
    authFetch('/conversations')
      .then((res) => res.json())
      .then(async (data: { id: string; title: string }[]) => {
        if (data.length === 0) {
          const id: string = await authFetch('/new_conversation').then((res) => res.json());
          setActiveConversationId(id);
          setConversations([{ id, title: 'New chat', participants: members }]);
          return;
        }
        const convos = data.map((c) => ({ id: c.id, title: c.title, participants: members }));
        setConversations(convos);
        setActiveConversationId(convos[0].id);
      });
  }, [authChecked]);

  const handleStartNewConversation = () => {
    setNewTitleDraft('');
    setIsCreatingNew(true);
  };

  const handleCancelNewConversation = () => {
    setIsCreatingNew(false);
    setNewTitleDraft('');
  };

  const handleConfirmNewConversation = async () => {
    const trimmed = newTitleDraft.trim();
    if (!trimmed) return;

    const id: string = await authFetch('/new_conversation').then((res) => res.json());
    const res = await authFetch(`/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: trimmed }),
    });
    if (!res.ok) return;

    setConversations((prev) => [{ id, title: trimmed, participants: members }, ...prev]);
    setActiveConversationId(id);
    setIsCreatingNew(false);
    setNewTitleDraft('');
  };

  const handleRename = (id: string, currentTitle?: string) => {
    setRenameTitle(currentTitle ?? '');
    setRenameConversationId(id);
    setRenameDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setDeleteTargetId(id);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    const id = deleteTargetId;

    const res = await authFetch(`/conversations/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      setDeleteTargetId(null);
      return;
    }

    const remaining = conversations.filter((c) => c.id !== id);

    if (remaining.length === 0) {
      const newId: string = await authFetch('/new_conversation').then((res) => res.json());
      setConversations([{ id: newId, title: 'New chat', participants: members }]);
      setActiveConversationId(newId);
    } else {
      setConversations(remaining);
      if (activeConversationId === id) {
        setActiveConversationId(remaining[0].id);
      }
    }
    setDeleteTargetId(null);
  };

  const handleSubmitRename = async () => {
    const trimmed = renameTitle.trim();
    if (!trimmed || !renameConversationId) return;

    const res = await authFetch(`/conversations/${renameConversationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: trimmed }),
    });
    if (!res.ok) return;

    setConversations((prev) =>
      prev.map((c) => (c.id === renameConversationId ? { ...c, title: trimmed } : c)),
    );
    setRenameDialogOpen(false);
  };

  const ConversationHeaderActions = () => {
    const { conversations: liveConversations, activeConversationId: liveActiveId } = useChat();
    const conversation = liveConversations.find((c) => c.id === liveActiveId);
    return (
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <Tooltip title="Rename conversation">
          <IconButton
            size="small"
            onClick={() => conversation && handleRename(conversation.id, conversation.title)}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete conversation">
          <IconButton
            size="small"
            onClick={() => conversation && handleDelete(conversation.id)}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    );
  };

  const ConversationListWithNewChat = forwardRef<HTMLDivElement, React.ComponentProps<typeof ChatConversationList>>(
    function ConversationListWithNewChat(props, ref) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            minHeight: 0,
            bgcolor: 'background.paper',
          }}
        >
          <Box
            sx={{
              p: 1,
              borderBottom: 1,
              borderColor: 'divider',
              bgcolor: 'background.paper',
            }}
          >
            {isCreatingNew ? (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <TextField
                  autoFocus
                  fullWidth
                  size="small"
                  placeholder="Conversation name"
                  value={newTitleDraft}
                  onChange={(event) => setNewTitleDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      void handleConfirmNewConversation();
                    }
                    if (event.key === 'Escape') {
                      event.preventDefault();
                      handleCancelNewConversation();
                    }
                  }}
                />
                <IconButton size="small" color="primary" onClick={() => void handleConfirmNewConversation()}>
                  <CheckIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" onClick={handleCancelNewConversation}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            ) : (
              <Button
                fullWidth
                size="small"
                variant="outlined"
                startIcon={<AddCommentIcon />}
                onClick={handleStartNewConversation}
              >
                New chat
              </Button>
            )}
          </Box>
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <ChatConversationList ref={ref} {...props} />
          </Box>
        </Box>
      );
    },
  );

  if (!authChecked) {
    return null;
  }

  return (
    <Box sx={{ height: 728 }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Tooltip title="Log out">
          <IconButton size="small" onClick={() => logout()}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <ChatBox
        adapter={adapter}
        members={members}
        activeConversationId={activeConversationId}
        onActiveConversationChange={setActiveConversationId}
        conversations={conversations}
        onConversationsChange={setConversations}
        variant="default"
        density="standard"
        suggestionsAutoSubmit={false}
        partRenderers={{
          // Renders the charts produced by the backend Visualization Planner
          // below the assistant message that carries them.
          'data-visualization': ({ part }) => (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                mt: 1,
                mb: 0.5,
                width: '100%',
              }}
            >
              {part.data.map((spec, index) => (
                <ChartRenderer key={index} spec={spec} />
              ))}
            </Box>
          ),
        }}
        features={{
          conversationList: true,
          conversationHeader: true,
          scrollToBottom: true,
          attachments: true,
          helperText: true,
          autoScroll: true,
          suggestions: true,
        }}
        slots={{
          conversationHeaderActions: ConversationHeaderActions,
          conversationList: ConversationListWithNewChat,
        }}
        sx={{ height: '100%' }}
      />
      <Dialog open={renameDialogOpen} onClose={() => setRenameDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Rename conversation</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label="Conversation name"
            value={renameTitle}
            onChange={(event) => setRenameTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                void handleSubmitRename();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleSubmitRename()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={deleteTargetId !== null} onClose={() => setDeleteTargetId(null)} fullWidth maxWidth="xs">
        <DialogTitle>Delete conversation?</DialogTitle>
        <DialogContent>
          This permanently deletes the conversation and all its messages. This cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTargetId(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => void handleConfirmDelete()}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}