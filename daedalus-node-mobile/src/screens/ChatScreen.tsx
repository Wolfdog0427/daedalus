import React from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useDaedalus } from '../daedalus/useDaedalus';
import { colors, spacing, fonts, radius } from '../theme';
import type { ChatMessage } from '../api/daedalusApi';

const SUGGESTIONS = [
  'What is the current status?',
  'How is alignment?',
  'Who am I?',
  'Show fleet health',
  'Any incidents?',
  'Help',
];

function isPreformatted(content: string): boolean {
  return content.includes('\n') && (content.includes('  ') || content.includes(':'));
}

const MessageBubble: React.FC<{ msg: ChatMessage }> = React.memo(({ msg }) => {
  const isOperator = msg.role === 'operator';
  const isSystem = msg.role === 'system';
  const pre = msg.role === 'daedalus' && isPreformatted(msg.content);

  let time = '';
  try {
    time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { /* ignore */ }

  return (
    <View style={[
      styles.msgRow,
      isOperator && styles.msgRowOperator,
      isSystem && styles.msgRowSystem,
    ]}>
      {!isOperator && !isSystem && (
        <View style={styles.msgAvatar}>
          <Text style={styles.msgAvatarText}>{'\u2666'}</Text>
        </View>
      )}
      <View style={styles.msgContent}>
        <View style={[
          styles.bubble,
          isOperator && styles.bubbleOperator,
          isSystem && styles.bubbleSystem,
          !isOperator && !isSystem && styles.bubbleDaedalus,
        ]}>
          {pre ? (
            <Text style={styles.preText}>{msg.content}</Text>
          ) : (
            <Text style={[
              styles.bubbleText,
              isOperator && styles.bubbleTextOperator,
              isSystem && styles.bubbleTextSystem,
            ]}>{msg.content}</Text>
          )}
        </View>
        <Text style={[styles.time, isOperator && styles.timeOperator]}>{time}</Text>
      </View>
    </View>
  );
});

const TypingIndicator: React.FC = () => (
  <View style={styles.typingRow}>
    <View style={styles.msgAvatar}>
      <Text style={styles.msgAvatarText}>{'\u2666'}</Text>
    </View>
    <View style={styles.typingBubble}>
      <ActivityIndicator size="small" color={colors.accent} />
      <Text style={styles.typingLabel}>Daedalus is thinking...</Text>
    </View>
  </View>
);

export const ChatScreen: React.FC = () => {
  const { chatMessages, chatSending, sendChat, clearChat, connection } = useDaedalus();
  const [input, setInput] = React.useState('');
  const listRef = React.useRef<FlatList>(null);

  const handleSend = React.useCallback(() => {
    if (!input.trim() || chatSending) return;
    sendChat(input.trim());
    setInput('');
  }, [input, chatSending, sendChat]);

  const handleSuggestion = React.useCallback((text: string) => {
    sendChat(text);
  }, [sendChat]);

  React.useEffect(() => {
    if (chatMessages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 150);
    }
  }, [chatMessages.length]);

  const showSuggestions = chatMessages.length <= 1 && !chatSending;

  const renderItem = React.useCallback(({ item }: { item: ChatMessage }) => (
    <MessageBubble msg={item} />
  ), []);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{'\u2666'}</Text>
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.headerName}>Daedalus</Text>
          <View style={styles.headerStatusRow}>
            <View style={[styles.headerDot, connection !== 'connected' && { backgroundColor: colors.yellow }]} />
            <Text style={styles.headerStatus}>
              {connection === 'connected' ? 'Online' : connection === 'error' ? 'Reconnecting...' : 'Connecting...'}
            </Text>
          </View>
        </View>
        <TouchableOpacity style={styles.clearBtn} onPress={clearChat} activeOpacity={0.6}>
          <Text style={styles.clearBtnText}>{'\u2672'}</Text>
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={chatMessages}
        keyExtractor={item => item.id}
        renderItem={renderItem}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        ListFooterComponent={chatSending ? <TypingIndicator /> : null}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>{'\u2666'}</Text>
            <Text style={styles.emptyTitle}>Talk to Daedalus</Text>
            <Text style={styles.emptyText}>
              Ask about system status, alignment, trust, governance, fleet health, or anything else.
            </Text>
          </View>
        }
      />

      {/* Suggestions */}
      {showSuggestions && (
        <View style={styles.suggestions}>
          {SUGGESTIONS.map(s => (
            <TouchableOpacity key={s} style={styles.pill} onPress={() => handleSuggestion(s)} activeOpacity={0.7}>
              <Text style={styles.pillText}>{s}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Input */}
      <View style={styles.inputArea}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Talk to Daedalus..."
          placeholderTextColor={colors.textFaint}
          onSubmitEditing={handleSend}
          returnKeyType="send"
          editable={!chatSending}
          multiline
          blurOnSubmit
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || chatSending) && styles.sendBtnDisabled]}
          onPress={handleSend}
          disabled={!input.trim() || chatSending}
          activeOpacity={0.7}
        >
          <Text style={styles.sendBtnText}>{'\u2191'}</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.surfaceElevated,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 15,
    color: colors.accent,
  },
  headerInfo: { flex: 1 },
  headerName: {
    fontSize: fonts.body,
    fontWeight: '600',
    color: colors.text,
  },
  headerStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  headerDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.green,
  },
  headerStatus: {
    fontSize: fonts.micro,
    color: colors.textMuted,
  },
  clearBtn: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceElevated,
  },
  clearBtnText: {
    fontSize: 16,
    color: colors.textMuted,
  },

  list: { flex: 1 },
  listContent: {
    padding: spacing.lg,
    gap: spacing.lg,
    flexGrow: 1,
  },

  msgRow: {
    maxWidth: '90%',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  msgRowOperator: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  msgRowSystem: {
    alignSelf: 'center',
    maxWidth: '92%',
  },

  msgAvatar: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.surfaceElevated,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  msgAvatarText: {
    fontSize: 10,
    color: colors.accent,
  },
  msgContent: {
    flex: 1,
  },

  bubble: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
  },
  bubbleOperator: {
    backgroundColor: colors.accentDim,
    borderWidth: 1,
    borderColor: colors.accentBorder,
    borderBottomRightRadius: spacing.xs,
  },
  bubbleDaedalus: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderBottomLeftRadius: spacing.xs,
  },
  bubbleSystem: {
    backgroundColor: colors.yellowDim,
    borderWidth: 1,
    borderColor: 'rgba(210, 153, 34, 0.12)',
    borderRadius: radius.sm,
  },

  bubbleText: {
    fontSize: fonts.body,
    lineHeight: 20,
    color: colors.textSecondary,
  },
  bubbleTextOperator: {
    color: colors.text,
  },
  bubbleTextSystem: {
    color: colors.textMuted,
    fontSize: fonts.small,
    textAlign: 'center',
  },
  preText: {
    fontFamily: 'monospace',
    fontSize: fonts.small,
    lineHeight: 18,
    color: colors.textSecondary,
  },

  time: {
    fontSize: fonts.micro,
    color: colors.textFaint,
    marginTop: 3,
    paddingHorizontal: spacing.xs,
  },
  timeOperator: {
    textAlign: 'right',
  },

  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    alignSelf: 'flex-start',
  },
  typingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  typingLabel: {
    fontSize: fonts.caption,
    color: colors.textFaint,
  },

  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 40,
    color: colors.textFaint,
    opacity: 0.3,
  },
  emptyTitle: {
    fontSize: fonts.subtitle,
    fontWeight: '600',
    color: colors.textMuted,
  },
  emptyText: {
    fontSize: fonts.body,
    color: colors.textFaint,
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: spacing.xxl,
  },

  suggestions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  pill: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm - 1,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  pillText: {
    fontSize: fonts.caption,
    color: colors.textMuted,
    fontWeight: '500',
  },

  inputArea: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    minHeight: 42,
    maxHeight: 100,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm + 2,
    fontSize: fonts.body,
    backgroundColor: colors.surfaceElevated,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.text,
    lineHeight: 20,
  },
  sendBtn: {
    width: 42,
    height: 42,
    borderRadius: radius.md,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    opacity: 0.3,
  },
  sendBtnText: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.bg,
  },
});
