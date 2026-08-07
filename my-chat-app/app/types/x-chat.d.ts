/**
 * Strong typing for the custom `data-visualization` chat message part.
 *
 * Registers the part payload type in @mui/x-chat-headless's `ChatDataPartMap`
 * so both the adapter stream chunks and the `partRenderers` callback get
 * `VisualizationSpec[]` instead of `unknown`.
 */
import type { VisualizationSpec } from '../components/ChartRenderer';

declare module '@mui/x-chat-headless/types' {
  interface ChatDataPartMap {
    'data-visualization': VisualizationSpec[];
  }
}
