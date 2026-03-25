import React from 'react';
import {
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import {
  fetchApprovalGate,
  submitChangeProposal,
  fetchRollbackRegistry,
  type ApprovalGateResponse,
  type ApprovalDecision,
  type ApprovalReasonBreakdown,
  type ChangeProposalKind,
  type RollbackRegistrySnapshot,
} from '../api/daedalusApi';
import { colors, spacing, radius, fonts } from '../theme';

const REASON_LABELS: Record<keyof ApprovalReasonBreakdown, string> = {
  alignmentOK: 'Alignment',
  confidenceOK: 'Confidence',
  impactOK: 'Impact',
  invariantsOK: 'Invariants',
  reversibleOK: 'Reversible',
  safeModeOK: 'Safe Mode',
  cooldownOK: 'Cooldown',
};

const PROPOSAL_KINDS: { value: ChangeProposalKind; label: string }[] = [
  { value: 'alignment_config', label: 'Alignment' },
  { value: 'governance_policy', label: 'Governance' },
  { value: 'regulation_tuning', label: 'Regulation' },
  { value: 'posture_shift', label: 'Posture' },
  { value: 'node_authority', label: 'Node Auth' },
  { value: 'identity_update', label: 'Identity' },
  { value: 'telemetry_config', label: 'Telemetry' },
  { value: 'other', label: 'Other' },
];

function ReasonBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <View style={[s.reasonBadge, ok ? s.reasonPass : s.reasonFail]}>
      <Text style={[s.reasonText, ok ? s.reasonTextPass : s.reasonTextFail]}>
        {ok ? '✓' : '×'} {label}
      </Text>
    </View>
  );
}

function DecisionCard({ decision }: { decision: ApprovalDecision }) {
  const time = new Date(decision.decidedAt).toLocaleTimeString();
  const approved = decision.autoApprove;

  return (
    <View style={[s.decisionCard, approved ? s.decisionApproved : s.decisionReview]}>
      <View style={s.decisionTop}>
        <View style={[s.verdictBadge, approved ? s.verdictApproved : s.verdictNeedsReview]}>
          <Text style={[s.verdictText, approved ? s.verdictTextApproved : s.verdictTextReview]}>
            {approved ? 'Auto-Approved' : 'Needs Review'}
          </Text>
        </View>
        <Text style={s.decisionTime}>{time}</Text>
      </View>
      <Text style={s.decisionDesc}>{decision.proposal.description}</Text>
      <View style={s.decisionMeta}>
        <View style={s.kindBadge}>
          <Text style={s.kindText}>{decision.proposal.kind}</Text>
        </View>
        <View style={[
          s.impactBadge,
          decision.derivedImpact === 'low' ? s.impactLow :
          decision.derivedImpact === 'medium' ? s.impactMedium : s.impactHigh
        ]}>
          <Text style={[
            s.impactText,
            decision.derivedImpact === 'low' ? s.impactTextLow :
            decision.derivedImpact === 'medium' ? s.impactTextMed : s.impactTextHigh
          ]}>
            {decision.derivedImpact.toUpperCase()}
          </Text>
        </View>
        <Text style={s.scoreText}>A:{decision.alignment}% C:{decision.confidence}%</Text>
      </View>
      <View style={s.reasons}>
        {(Object.entries(decision.reasons) as [keyof ApprovalReasonBreakdown, boolean][]).map(([key, ok]) => (
          <ReasonBadge key={key} label={REASON_LABELS[key]} ok={ok} />
        ))}
      </View>
    </View>
  );
}

export const EvolutionScreen: React.FC = () => {
  const [gate, setGate] = React.useState<ApprovalGateResponse | null>(null);
  const [rollback, setRollback] = React.useState<RollbackRegistrySnapshot | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [refreshing, setRefreshing] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [selectedKind, setSelectedKind] = React.useState<ChangeProposalKind>('alignment_config');
  const [description, setDescription] = React.useState('');
  const [submitResult, setSubmitResult] = React.useState<ApprovalDecision | null>(null);

  const load = React.useCallback(async () => {
    try {
      const [g, r] = await Promise.all([fetchApprovalGate(), fetchRollbackRegistry()]);
      setGate(g);
      setRollback(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    }
  }, []);

  React.useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10_000);
    return () => clearInterval(id);
  }, [load]);

  const onRefresh = React.useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const handleSubmit = React.useCallback(async () => {
    if (!description.trim() || submitting) return;
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const result = await submitChangeProposal(selectedKind, description.trim());
      setSubmitResult(result);
      setDescription('');
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  }, [selectedKind, description, submitting, load]);

  const decisions = gate?.recentDecisions ?? [];
  const needsReview = decisions.filter(d => !d.autoApprove).length;

  return (
    <ScrollView
      style={s.container}
      contentContainerStyle={s.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={colors.accent}
          colors={[colors.accent]}
          progressBackgroundColor={colors.surface}
        />
      }
    >
      <View style={s.header}>
        <Text style={s.title}>◈ Evolution</Text>
        <View style={[s.headerBadge, needsReview > 0 ? s.headerBadgePending : s.headerBadgeClear]}>
          <Text style={[s.headerBadgeText, needsReview > 0 ? s.headerBadgeTextPending : s.headerBadgeTextClear]}>
            {needsReview > 0 ? `${needsReview} awaiting review` : 'All clear'}
          </Text>
        </View>
      </View>

      {error && (
        <View style={s.errorBox}>
          <Text style={s.errorText}>{error}</Text>
        </View>
      )}

      {gate && (
        <View style={s.gateStrip}>
          <Text style={s.gateItem}>
            Align ≥ <Text style={s.gateVal}>{gate.config.alignmentThreshold}%</Text>
          </Text>
          <Text style={s.gateItem}>
            Conf ≥ <Text style={s.gateVal}>{gate.config.confidenceThreshold}%</Text>
          </Text>
          <Text style={s.gateItem}>
            Safe: <Text style={s.gateVal}>{gate.config.allowDuringSafeMode ? 'yes' : 'no'}</Text>
          </Text>
        </View>
      )}

      <View style={s.form}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.kindScroll}>
          <View style={s.kindRow}>
            {PROPOSAL_KINDS.map(pk => (
              <TouchableOpacity
                key={pk.value}
                style={[s.kindChip, selectedKind === pk.value && s.kindChipActive]}
                onPress={() => setSelectedKind(pk.value)}
                activeOpacity={0.7}
              >
                <Text style={[s.kindChipText, selectedKind === pk.value && s.kindChipTextActive]}>
                  {pk.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>

        <View style={s.inputRow}>
          <TextInput
            style={s.input}
            placeholder="Describe the proposed evolution..."
            placeholderTextColor={colors.textFaint}
            value={description}
            onChangeText={setDescription}
            onSubmitEditing={handleSubmit}
            returnKeyType="send"
          />
          <TouchableOpacity
            style={[s.submitBtn, (!description.trim() || submitting) && s.submitBtnDisabled]}
            onPress={handleSubmit}
            disabled={!description.trim() || submitting}
            activeOpacity={0.7}
          >
            {submitting ? (
              <ActivityIndicator size="small" color={colors.accent} />
            ) : (
              <Text style={s.submitText}>Submit</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {submitResult && <DecisionCard decision={submitResult} />}

      {rollback && (
        <View style={s.registryCard}>
          <Text style={s.registryTitle}>Change Registry</Text>
          <View style={s.registryStats}>
            <Text style={s.statText}>Active: <Text style={s.statNum}>{rollback.activeChanges.length}</Text></Text>
            <Text style={s.statText}>Accepted: <Text style={s.statNum}>{rollback.acceptedCount}</Text></Text>
            <Text style={s.statText}>Rolled back: <Text style={s.statNum}>{rollback.rolledBackCount}</Text></Text>
          </View>
        </View>
      )}

      {decisions.length > 0 ? (
        decisions.slice().reverse().slice(0, 10).map((d, i) => (
          <DecisionCard key={d.proposal.id ?? `d-${i}`} decision={d} />
        ))
      ) : (
        <View style={s.emptyBox}>
          <Text style={s.emptyText}>No proposals yet. Submit one above to begin.</Text>
        </View>
      )}
    </ScrollView>
  );
};

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: 40 },

  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: fonts.title, fontWeight: '700', color: colors.text },
  headerBadge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: radius.pill },
  headerBadgePending: { backgroundColor: colors.yellowDim, borderWidth: 1, borderColor: 'rgba(210,153,34,0.3)' },
  headerBadgeClear: { backgroundColor: colors.greenDim, borderWidth: 1, borderColor: 'rgba(63,185,80,0.2)' },
  headerBadgeText: { fontSize: fonts.caption, fontWeight: '600' },
  headerBadgeTextPending: { color: colors.yellow },
  headerBadgeTextClear: { color: colors.green },

  errorBox: { backgroundColor: colors.redDim, borderWidth: 1, borderColor: 'rgba(248,81,73,0.15)', borderRadius: radius.md, padding: spacing.md },
  errorText: { color: colors.red, fontSize: fonts.small },

  gateStrip: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, padding: spacing.md, backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderSubtle },
  gateItem: { fontSize: fonts.small, color: colors.textMuted },
  gateVal: { fontWeight: '700', color: colors.textSecondary },

  form: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, padding: spacing.md, gap: spacing.sm },
  kindScroll: { marginBottom: spacing.xs },
  kindRow: { flexDirection: 'row', gap: spacing.xs },
  kindChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, backgroundColor: 'transparent' },
  kindChipActive: { backgroundColor: colors.accentDim, borderColor: colors.accentBorder },
  kindChipText: { fontSize: fonts.caption, color: colors.textMuted, fontWeight: '500' },
  kindChipTextActive: { color: colors.accent },
  inputRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  input: { flex: 1, backgroundColor: colors.surfaceElevated, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingHorizontal: 12, paddingVertical: 10, color: colors.text, fontSize: fonts.body },
  submitBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: radius.md, backgroundColor: colors.accentDim, borderWidth: 1, borderColor: colors.accentBorder },
  submitBtnDisabled: { opacity: 0.4 },
  submitText: { color: colors.accent, fontWeight: '600', fontSize: fonts.body },

  decisionCard: { borderRadius: radius.md, padding: spacing.md, gap: spacing.xs, borderWidth: 1 },
  decisionApproved: { backgroundColor: colors.greenDim, borderColor: 'rgba(63,185,80,0.15)' },
  decisionReview: { backgroundColor: colors.yellowDim, borderColor: 'rgba(210,153,34,0.2)' },
  decisionTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  verdictBadge: { paddingHorizontal: 10, paddingVertical: 2, borderRadius: radius.pill },
  verdictApproved: { backgroundColor: 'rgba(63,185,80,0.12)' },
  verdictNeedsReview: { backgroundColor: 'rgba(210,153,34,0.12)' },
  verdictText: { fontSize: fonts.caption, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.4 },
  verdictTextApproved: { color: colors.green },
  verdictTextReview: { color: colors.yellow },
  decisionTime: { fontSize: fonts.micro, color: colors.textFaint },
  decisionDesc: { fontSize: fonts.body, color: colors.textSecondary, lineHeight: 20 },
  decisionMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, alignItems: 'center' },
  kindBadge: { paddingHorizontal: 8, paddingVertical: 1, borderRadius: radius.pill, backgroundColor: colors.accentDim, borderWidth: 1, borderColor: colors.accentBorder },
  kindText: { fontSize: fonts.micro, color: colors.accent },
  impactBadge: { paddingHorizontal: 8, paddingVertical: 1, borderRadius: radius.pill, borderWidth: 1 },
  impactLow: { borderColor: 'rgba(63,185,80,0.2)', backgroundColor: colors.greenDim },
  impactMedium: { borderColor: 'rgba(210,153,34,0.2)', backgroundColor: colors.yellowDim },
  impactHigh: { borderColor: 'rgba(248,81,73,0.2)', backgroundColor: colors.redDim },
  impactText: { fontSize: fonts.micro, fontWeight: '600' },
  impactTextLow: { color: colors.green },
  impactTextMed: { color: colors.yellow },
  impactTextHigh: { color: colors.red },
  scoreText: { fontSize: fonts.micro, color: colors.textMuted },
  reasons: { flexDirection: 'row', flexWrap: 'wrap', gap: 4 },
  reasonBadge: { paddingHorizontal: 8, paddingVertical: 1, borderRadius: radius.pill, borderWidth: 1 },
  reasonPass: { borderColor: 'rgba(63,185,80,0.15)', backgroundColor: 'rgba(63,185,80,0.06)' },
  reasonFail: { borderColor: 'rgba(248,81,73,0.15)', backgroundColor: 'rgba(248,81,73,0.06)' },
  reasonText: { fontSize: fonts.micro, fontWeight: '600' },
  reasonTextPass: { color: colors.green },
  reasonTextFail: { color: colors.red },

  registryCard: { backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderSubtle, padding: spacing.md, gap: spacing.xs },
  registryTitle: { fontSize: fonts.small, fontWeight: '600', color: colors.textSecondary, textTransform: 'uppercase', letterSpacing: 0.3 },
  registryStats: { flexDirection: 'row', gap: spacing.lg },
  statText: { fontSize: fonts.small, color: colors.textMuted },
  statNum: { fontWeight: '700', color: colors.textSecondary },

  emptyBox: { padding: spacing.lg, alignItems: 'center' },
  emptyText: { color: colors.textFaint, fontSize: fonts.body, textAlign: 'center' },
});
