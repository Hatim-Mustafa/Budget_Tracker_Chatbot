'use client';

import { alpha, createTheme } from '@mui/material/styles';

/**
 * App-wide MUI theme.
 *
 * A modern, light "messaging" look built around an indigo → violet gradient,
 * soft lavender-tinted surfaces and generous rounding. The x-chat components
 * are styled here (bubbles, composer, sidebar, suggestions) so the whole app
 * shares one design language without touching the ChatBox feature code.
 */

const GRADIENT = 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #a855f7 100%)';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#6366f1', light: '#818cf8', dark: '#4f46e5', contrastText: '#ffffff' },
    secondary: { main: '#0ea5e9', light: '#38bdf8', dark: '#0284c7' },
    success: { main: '#16a34a' },
    warning: { main: '#d97706' },
    error: { main: '#e11d48' },
    background: { default: '#eef1fa', paper: '#ffffff' },
    text: { primary: '#0f172a', secondary: '#64748b' },
    divider: 'rgba(15, 23, 42, 0.08)',
    action: {
      hover: alpha('#6366f1', 0.06),
      selected: alpha('#6366f1', 0.12),
    },
  },
  shape: { borderRadius: 16 },
  typography: {
    fontFamily:
      "var(--font-geist-sans), 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    h4: { fontWeight: 700, letterSpacing: '-0.02em' },
    h5: { fontWeight: 700, letterSpacing: '-0.02em' },
    h6: { fontWeight: 600, letterSpacing: '-0.01em' },
    button: { textTransform: 'none', fontWeight: 600 },
    body1: { lineHeight: 1.6 },
    body2: { lineHeight: 1.55 },
  },
  components: {
    // ---------------------------------------------------------------- core
    MuiCssBaseline: {
      styleOverrides: (theme) => ({
        body: {
          background: 'linear-gradient(160deg, #eef1fa 0%, #f6f4ff 45%, #eef7ff 100%)',
          backgroundAttachment: 'fixed',
          color: theme.palette.text.primary,
          WebkitFontSmoothing: 'antialiased',
          '& ::selection': {
            background: alpha(theme.palette.primary.main, 0.18),
          },
        },
        '*::-webkit-scrollbar': { width: 8, height: 8 },
        '*::-webkit-scrollbar-track': { background: 'transparent' },
        '*::-webkit-scrollbar-thumb': {
          background: alpha('#64748b', 0.35),
          borderRadius: 999,
          '&:hover': { background: alpha('#64748b', 0.55) },
        },
      }),
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 999, boxShadow: 'none' },
        containedPrimary: {
          background: GRADIENT,
          boxShadow: '0 6px 18px rgba(99, 102, 241, 0.35)',
          '&:hover': {
            boxShadow: '0 8px 22px rgba(99, 102, 241, 0.45)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 20 },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 24,
          padding: 4,
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: { root: { fontWeight: 700, fontSize: '1.15rem' } },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: alpha('#6366f1', 0.5),
            },
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 12 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 8,
          fontSize: '0.75rem',
          fontWeight: 500,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          transition: 'background-color 0.15s ease, color 0.15s ease',
        },
      },
    },

    // ------------------------------------------------------------- x-chat
    MuiChatBox: {
      styleOverrides: {
        root: {
          borderRadius: 24,
          overflow: 'hidden',
          backgroundColor: 'transparent',
        },
        conversationsPane: {
          backgroundColor: 'rgba(255, 255, 255, 0.72)',
          backdropFilter: 'blur(12px)',
          borderRight: '1px solid rgba(15, 23, 42, 0.08)',
        },
        threadPane: {
          backgroundColor: 'rgba(255, 255, 255, 0.4)',
        },
      },
    },
    MuiChatConversationList: {
      styleOverrides: {
        scroller: {
          borderRight: 'none',
          backgroundColor: 'transparent',
          padding: '8px 10px 10px',
        },
        viewport: { gap: 2 },
        item: ({ theme }) => ({
          margin: '2px 4px',
          padding: theme.spacing(1.25, 1.5),
          borderRadius: 14,
          gap: theme.spacing(1.5),
          '&:hover': {
            backgroundColor: alpha(theme.palette.primary.main, 0.08),
          },
        }),
        itemSelected: {
          backgroundColor: alpha('#6366f1', 0.14),
          '&:hover': { backgroundColor: alpha('#6366f1', 0.18) },
        },
        itemAvatar: ({ theme }) => ({
          width: 38,
          height: 38,
          borderRadius: '50%',
          background: GRADIENT,
          color: '#fff',
          fontWeight: 700,
          fontSize: '0.875rem',
          boxShadow: '0 2px 8px rgba(99, 102, 241, 0.35)',
        }),
        itemTitle: ({ theme }) => ({
          fontWeight: 600,
          fontSize: '0.9rem',
        }),
        itemPreview: ({ theme }) => ({
          fontSize: '0.8rem',
          color: theme.palette.text.secondary,
        }),
        itemTimestamp: ({ theme }) => ({
          fontSize: '0.7rem',
          color: theme.palette.text.secondary,
        }),
      },
    },
    MuiChatConversation: {
      styleOverrides: {
        header: {
          backgroundColor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(15, 23, 42, 0.06)',
          minHeight: 60,
        },
      },
    },
    MuiChatMessageList: {
      styleOverrides: {
        root: { backgroundColor: 'transparent' },
      },
    },
    MuiChatMessage: {
      styleOverrides: {
        root: ({ theme }) => ({
          paddingBlock: theme.spacing(0.75),
        }),
        bubble: ({ theme, ownerState }) => {
          const isOwn = ownerState?.isOwnMessage ?? false;
          if (isOwn) {
            return {
              background: GRADIENT,
              color: '#fff',
              boxShadow: '0 6px 16px rgba(99, 102, 241, 0.28)',
              borderRadius: '18px 18px 4px 18px',
              '& code': { background: alpha('#fff', 0.18) },
              '& pre': { background: alpha('#0f172a', 0.25) },
            };
          }
          return {
            background: '#ffffff',
            border: '1px solid rgba(15, 23, 42, 0.05)',
            boxShadow: '0 1px 3px rgba(15, 23, 42, 0.06)',
            borderRadius: '18px 18px 18px 4px',
          };
        },
        inlineMeta: {
          color: alpha('#ffffff', 0.85),
          fontSize: '0.72rem',
        },
      },
    },
    MuiChatComposer: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 24,
          border: '1px solid rgba(15, 23, 42, 0.08)',
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          boxShadow: '0 8px 28px rgba(15, 23, 42, 0.08)',
          margin: theme.spacing(0, 2.5, 2.5),
          padding: theme.spacing(1, 1.75),
          '&:focus-within:not([data-disabled])': {
            borderColor: '#6366f1',
            boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.15), 0 8px 28px rgba(15, 23, 42, 0.08)',
          },
        }),
        sendButton: ({ theme }) => ({
          width: 42,
          height: 42,
          borderRadius: '50%',
          background: GRADIENT,
          color: '#fff',
          boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
          transition: 'transform 0.12s ease, box-shadow 0.12s ease',
          '&:hover': {
            background: GRADIENT,
            transform: 'translateY(-1px)',
            boxShadow: '0 6px 16px rgba(99, 102, 241, 0.5)',
          },
          '&:disabled': {
            background: '#cbd5e1',
            color: '#fff',
            boxShadow: 'none',
            opacity: 1,
          },
        }),
        attachButton: ({ theme }) => ({
          borderRadius: '50%',
          width: 42,
          height: 42,
          color: theme.palette.text.secondary,
          '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.1), color: theme.palette.primary.main },
        }),
      },
    },
    MuiChatSuggestions: {
      styleOverrides: {
        item: ({ theme }) => ({
          borderRadius: 999,
          border: '1px solid rgba(99, 102, 241, 0.25)',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          color: theme.palette.primary.dark,
          fontWeight: 600,
          fontSize: '0.85rem',
          padding: theme.spacing(0.75, 1.5),
          transition: 'all 0.15s ease',
          '&:hover': {
            backgroundColor: '#6366f1',
            borderColor: '#6366f1',
            color: '#fff',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.35)',
          },
        }),
      },
    },
    MuiChatScrollToBottomAffordance: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: '50%',
          boxShadow: '0 4px 16px rgba(15, 23, 42, 0.18)',
          '&:hover': { backgroundColor: theme.palette.primary.main, color: '#fff' },
        }),
      },
    },
  },
});
