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
  Typography,
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import AddCommentIcon from '@mui/icons-material/AddComment';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import InsightsIcon from '@mui/icons-material/Insights';
import BarChartIcon from '@mui/icons-material/BarChart';
import SearchIcon from '@mui/icons-material/Search';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
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

/** Brand mark used in the app header. */
export function BrandLogo({ size = 40 }: { size?: number }) {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        borderRadius: size / 2.4,
        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #a855f7 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        boxShadow: '0 6px 18px rgba(99, 102, 241, 0.4)',
        flexShrink: 0,
      }}
    >
      <ChatBubbleOutlineRoundedIcon sx={{ fontSize: size * 0.52 }} />
    </Box>
  );
}

/** Quick-start prompts shown in the welcome state. */
const QUICK_PROMPTS: { icon: typeof InsightsIcon; title: string; prompt: string }[] = [
  {
    icon: InsightsIcon,
    title: 'Explore the data',
    prompt: 'Summarise the data we have available and highlight the key trends.',
  },
  {
    icon: BarChartIcon,
    title: 'Visualise something',
    prompt: 'Create a chart that shows the most important insights in the data.',
  },
  {
    icon: SearchIcon,
    title: 'Ask the knowledge base',
    prompt: 'What do we know about this project? Search the knowledge base for context.',
  },
  {
    icon: AccountBalanceWalletIcon,
    title: 'Analyse the budget',
    prompt: 'Analyse the budget and show me where we are overspending.',
  },
];

/**
 * Welcome hero rendered inside the thread when the active conversation has no
 * messages yet. Clicking a prompt sends it straight to the assistant.
 */
function WelcomeState() {
  const { sendMessage, activeConversationId } = useChat();

  const runPrompt = (text: string) => {
    void sendMessage({
      conversationId: activeConversationId,
      parts: [{ type: 'text', text }],
    });
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        gap: 3,
        px: { xs: 2, sm: 4 },
        py: 4,
        height: '100%',
        overflow: 'auto',
      }}
    >
      <Box
        sx={{
          width: 72,
          height: 72,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #a855f7 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          boxShadow: '0 12px 32px rgba(99, 102, 241, 0.45)',
        }}
      >
        <AutoAwesomeIcon sx={{ fontSize: 36 }} />
      </Box>

      <Box>
        <Typography
          variant="h4"
          sx={{ fontSize: { xs: '1.6rem', sm: '2rem' }, fontWeight: 700, mb: 1 }}
        >
          How can I help you today?
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 460, mx: 'auto' }}>
          Ask questions about your data in plain language — I can summarise, analyse and
          answer with beautiful charts.
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 1.5,
          width: '100%',
          maxWidth: 640,
          mt: 1,
        }}
      >
        {QUICK_PROMPTS.map(({ icon: PromptIcon, title, prompt }) => (
          <Button
            key={title}
            variant="outlined"
            onClick={() => runPrompt(prompt)}
            sx={{
              justifyContent: 'flex-start',
              textAlign: 'left',
              p: 2,
              borderRadius: 18,
              borderColor: 'rgba(99, 102, 241, 0.25)',
              backgroundColor: 'rgba(255, 255, 255, 0.85)',
              backdropFilter: 'blur(8px)',
              textTransform: 'none',
              '&:hover': {
                borderColor: '#6366f1',
                backgroundColor: '#fff',
                boxShadow: '0 8px 24px rgba(99, 102, 241, 0.18)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(168,85,247,0.12))',
                  color: '#6366f1',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <PromptIcon fontSize="small" />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {title}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {prompt}
                </Typography>
              </Box>
              <ArrowForwardIcon fontSize="small" sx={{ color: 'text.disabled', flexShrink: 0 }} />
            </Box>
          </Button>
        ))}
      </Box>
    </Box>
  );
}

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
            bgcolor: 'transparent',
          }}
        >
          <Box sx={{ p: 1.25, pt: 1.5 }}>
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
                variant="contained"
                startIcon={<AddCommentIcon />}
                onClick={handleStartNewConversation}
                sx={{ py: 1, fontSize: '0.875rem' }}
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
    <Box
      sx={{
        height: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* App header */}
      <Box
        component="header"
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          px: { xs: 2, sm: 3 },
          py: 1.5,
          flexShrink: 0,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0 }}>
          <BrandLogo />
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 800, lineHeight: 1.15, letterSpacing: '-0.01em' }}
            >
              Insight Chat
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>
              Your data, in conversation
            </Typography>
          </Box>
        </Box>
        <Tooltip title="Log out">
          <IconButton
            size="small"
            onClick={() => logout()}
            sx={{
              border: '1px solid rgba(15, 23, 42, 0.08)',
              bgcolor: 'rgba(255, 255, 255, 0.7)',
              color: 'text.secondary',
              '&:hover': { bgcolor: 'rgba(225, 29, 72, 0.08)', color: 'error.main' },
            }}
          >
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Chat */}
      <Box sx={{ flex: 1, minHeight: 0, px: { xs: 1, sm: 2 }, pb: { xs: 1, sm: 2 } }}>
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
          emptyState: WelcomeState,
        }}
        sx={{ height: '100%' }}
      />
      </Box>
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
        <DialogActions sx={{ px: 3, pb: 2 }}>
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
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTargetId(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => void handleConfirmDelete()}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}