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
  fetchPendingProposals,
  fetchProposalHistory,
  approveDaedalusProposal,
  denyDaedalusProposal,
  type ApprovalGateResponse,
  type ApprovalDecision,
  type ApprovalReasonBreakdown,
  type ChangeProposalKind,
  type RollbackRegistrySnapshot,
  type DaedalusProposal,
  type ProposalHistoryEntry,
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

const PROPOSAL_KIND_META: Record<string, { label: string; color: string }> = {
  alignment_boost: { label: 'Alignment', color: colors.accent },
  regulation_tune: { label: 'Regulation', color: colors.accent },
  sensitivity_reduction: { label: 'Sensitivity', color: colors.accent },
  safe_mode_recovery: { label: 'Recovery', color: colors.accent },
  drift_correction: { label: 'Drift Fix', color: colors.accent },
  resilience_upgrade: { label: 'Resilience', color: '#bc8cff' },
  capability_expansion: { label: 'Capability', color: '#39d353' },
  monitoring_enhancement: { label: 'Monitoring', color: '#bc8cff' },
  architecture_improvement: { label: 'Architecture', color: '#bc8cff' },
  pattern_learning: { label: 'Learning', color: '#39d353' },
  trust_recovery_protocol: { label: 'Trust', color: '#bc8cff' },
  fleet_expansion: { label: 'Fleet', color: '#39d353' },
  self_assessment: { label: 'Self-Check', color: '#bc8cff' },
};

function DaedalusProposalCard({ proposal, onApprove, onDeny }: { proposal: DaedalusProposal; onApprove: (id: string) => void; onDeny: (id: string) => void }) {
  const ageS = Math.round((Date.now() - proposal.createdAt) / 1000);
  const ageStr = ageS < 60 ? `${ageS}s ago` : `${Math.round(ageS / 60)}m ago`;
  const alColor = proposal.alignment >= 85 ? colors.green : proposal.alignment >= 70 ? colors.yellow : colors.red;
  const coColor = proposal.confidence >= 80 ? colors.green : proposal.confidence >= 60 ? colors.yellow : colors.red;
  const kindMeta = PROPOSAL_KIND_META[proposal.kind] ?? { label: proposal.kind, color: colors.accent };

  return (
    <View style={s.dpCard}>
      <View style={s.dpHeader}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 }}>
          <Text style={s.dpTitle}>◈ {proposal.title}</Text>
          <View style={[s.kindBadge, { borderColor: kindMeta.color + '33', backgroundColor: kindMeta.color + '14' }]}>
            <Text style={[s.kindText, { color: kindMeta.color }]}>{kindMeta.label}</Text>
          </View>
        </View>
        <Text style={s.dpAge}>{ageStr}</Text>
      </View>
      {/* Recommendation banner */}
      {(() => {
        const pass = (proposal.alignment >= 85 ? 1 : 0) + (proposal.confidence >= 80 ? 1 : 0) + (proposal.impact === 'low' ? 1 : 0) + (!proposal.touchesInvariants ? 1 : 0) + (proposal.reversible ? 1 : 0);
        const level = (pass >= 4 && !proposal.touchesInvariants && proposal.reversible) ? 'safe' : (proposal.touchesInvariants || !proposal.reversible || proposal.impact === 'high') ? 'caution' : 'review';
        const label = level === 'safe' ? 'Low Risk' : level === 'caution' ? 'Review Carefully' : 'Moderate Risk';
        const color = level === 'safe' ? colors.green : level === 'caution' ? colors.red : colors.yellow;
        return (
          <View style={[s.dpRec, { borderColor: color + '33', backgroundColor: color + '0A' }]}>
            <Text style={[s.dpRecLabel, { color }]}>{label}</Text>
            <Text style={[s.dpRecDetail, { color }]}>{pass}/5 axes pass</Text>
          </View>
        );
      })()}

      <Text style={s.dpDesc}>{proposal.description}</Text>
      <Text style={s.dpRationale}>{proposal.rationale}</Text>

      {/* Alignment & Confidence */}
      <View style={s.dpMetrics}>
        <Text style={[s.dpMetric, { color: alColor }]}>Alignment: {proposal.alignment}%</Text>
        <Text style={[s.dpMetric, { color: coColor }]}>Confidence: {proposal.confidence}%</Text>
        <View style={[s.impactBadge, proposal.impact === 'low' ? s.impactLow : proposal.impact === 'medium' ? s.impactMedium : s.impactHigh]}>
          <Text style={[s.impactText, proposal.impact === 'low' ? s.impactTextLow : proposal.impact === 'medium' ? s.impactTextMed : s.impactTextHigh]}>
            {proposal.impact.toUpperCase()}
          </Text>
        </View>
      </View>

      {/* Safety axes */}
      <View style={s.dpAxes}>
        <Text style={[s.dpAxisBadge, { color: proposal.touchesInvariants ? colors.red : colors.green }]}>
          {proposal.touchesInvariants ? '⚠ Invariants' : '✓ Invariants'}
        </Text>
        <Text style={[s.dpAxisBadge, { color: proposal.reversible ? colors.green : colors.red }]}>
          {proposal.reversible ? '✓ Reversible' : '⚠ Irreversible'}
        </Text>
      </View>

      {/* Payload: what will change */}
      {Object.keys(proposal.payload ?? {}).length > 0 && (
        <View style={s.dpPayload}>
          <Text style={s.dpPayloadTitle}>Proposed changes</Text>
          {Object.entries(proposal.payload).map(([k, v]) => (
            <View key={k} style={s.dpPayloadRow}>
              <Text style={s.dpPayloadKey}>{k.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}</Text>
              <Text style={s.dpPayloadArrow}>→</Text>
              <Text style={s.dpPayloadVal}>{typeof v === 'number' ? (Number.isInteger(v) ? String(v) : (v as number).toFixed(3)) : String(v)}</Text>
            </View>
          ))}
        </View>
      )}

      <View style={s.dpActions}>
        <TouchableOpacity style={s.dpApprove} onPress={() => onApprove(proposal.id)} activeOpacity={0.7}>
          <Text style={s.dpApproveText}>Approve</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.dpDeny} onPress={() => onDeny(proposal.id)} activeOpacity={0.7}>
          <Text style={s.dpDenyText}>Deny</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export const EvolutionScreen: React.FC = () => {
  const [pending, setPending] = React.useState<DaedalusProposal[]>([]);
  const [history, setHistory] = React.useState<ProposalHistoryEntry[]>([]);
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
      const [p, h, g, r] = await Promise.all([
        fetchPendingProposals(),
        fetchProposalHistory(),
        fetchApprovalGate(),
        fetchRollbackRegistry(),
      ]);
      setPending(p);
      setHistory(h);
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

  const handleApprove = React.useCallback(async (id: string) => {
    try { await approveDaedalusProposal(id); void load(); } catch { setError('Approval failed'); }
  }, [load]);

  const handleDeny = React.useCallback(async (id: string) => {
    try { await denyDaedalusProposal(id); void load(); } catch { setError('Denial failed'); }
  }, [load]);

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
        <View style={[s.headerBadge, pending.length > 0 ? s.headerBadgePending : s.headerBadgeClear]}>
          <Text style={[s.headerBadgeText, pending.length > 0 ? s.headerBadgeTextPending : s.headerBadgeTextClear]}>
            {pending.length > 0 ? `${pending.length} awaiting approval` : 'All clear'}
          </Text>
        </View>
      </View>

      {error && (
        <View style={s.errorBox}>
          <Text style={s.errorText}>{error}</Text>
        </View>
      )}

      {pending.length > 0 && (
        <View style={s.sectionBox}>
          <Text style={s.sectionTitle}>Daedalus Proposals</Text>
          {pending.map(p => (
            <DaedalusProposalCard key={p.id} proposal={p} onApprove={handleApprove} onDeny={handleDeny} />
          ))}
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

      {history.length > 0 && (
        <View style={s.sectionBox}>
          <Text style={s.sectionTitle}>Proposal History</Text>
          {history.slice().reverse().slice(0, 12).map(entry => {
            const deltaColor = entry.effectDelta == null ? colors.textFaint : entry.effectDelta > 0 ? colors.green : entry.effectDelta < 0 ? colors.red : colors.textMuted;
            return (
              <View key={entry.id} style={[s.histRow, entry.status === 'denied' ? s.histDenied : s.histApproved]}>
                <View style={s.histTop}>
                  <Text style={s.histTitle}>{entry.title}</Text>
                  <Text style={s.histStatus}>{entry.status.replace('_', ' ')}</Text>
                </View>
                {entry.effectDelta != null && (
                  <Text style={[s.histDelta, { color: deltaColor }]}>
                    Effect: {entry.effectDelta > 0 ? '+' : ''}{entry.effectDelta.toFixed(1)}%
                  </Text>
                )}
              </View>
            );
          })}
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

  sectionBox: { gap: spacing.sm },
  sectionTitle: { fontSize: fonts.small, fontWeight: '600', color: colors.textSecondary, textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: spacing.xs },

  dpCard: { backgroundColor: 'rgba(88,166,255,0.03)', borderWidth: 1, borderColor: 'rgba(88,166,255,0.15)', borderRadius: radius.md, padding: spacing.md, gap: spacing.sm },
  dpHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  dpTitle: { fontSize: fonts.body, fontWeight: '600', color: colors.text, flex: 1 },
  dpAge: { fontSize: fonts.micro, color: colors.textFaint },
  dpDesc: { fontSize: fonts.body, color: colors.textSecondary, lineHeight: 20 },
  dpRationale: { fontSize: fonts.small, color: colors.textMuted, lineHeight: 18, paddingLeft: spacing.sm, borderLeftWidth: 2, borderLeftColor: 'rgba(88,166,255,0.2)' },
  dpMetrics: { flexDirection: 'row', gap: spacing.md, alignItems: 'center' },
  dpMetric: { fontSize: fonts.body, fontWeight: '700' },
  dpRec: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.sm, borderWidth: 1 },
  dpRecLabel: { fontSize: fonts.micro, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.3 } as any,
  dpRecDetail: { fontSize: fonts.caption, opacity: 0.85 },
  dpAxes: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
  dpAxisBadge: { fontSize: fonts.caption, fontWeight: '600' },
  dpPayload: { backgroundColor: 'rgba(0,0,0,0.2)', borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: spacing.sm },
  dpPayloadTitle: { fontSize: fonts.micro, fontWeight: '600', color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 4 } as any,
  dpPayloadRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dpPayloadKey: { fontSize: fonts.caption, color: colors.textSecondary, fontWeight: '500' },
  dpPayloadArrow: { fontSize: fonts.caption, color: colors.accent },
  dpPayloadVal: { fontSize: fonts.caption, color: colors.accent, fontWeight: '700' },
  dpActions: { flexDirection: 'row', gap: spacing.sm },
  dpApprove: { flex: 1, paddingVertical: 10, borderRadius: radius.md, backgroundColor: 'rgba(63,185,80,0.1)', borderWidth: 1, borderColor: 'rgba(63,185,80,0.3)', alignItems: 'center' },
  dpApproveText: { color: colors.green, fontWeight: '600', fontSize: fonts.body },
  dpDeny: { flex: 1, paddingVertical: 10, borderRadius: radius.md, backgroundColor: 'rgba(248,81,73,0.06)', borderWidth: 1, borderColor: 'rgba(248,81,73,0.2)', alignItems: 'center' },
  dpDenyText: { color: colors.red, fontWeight: '600', fontSize: fonts.body },

  histRow: { borderRadius: radius.sm, padding: spacing.sm, borderWidth: 1 },
  histApproved: { backgroundColor: 'rgba(63,185,80,0.03)', borderColor: 'rgba(63,185,80,0.1)' },
  histDenied: { backgroundColor: 'rgba(248,81,73,0.03)', borderColor: 'rgba(248,81,73,0.1)' },
  histTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  histTitle: { fontSize: fonts.small, fontWeight: '600', color: colors.textSecondary },
  histStatus: { fontSize: fonts.micro, fontWeight: '600', color: colors.textMuted, textTransform: 'uppercase' },
  histDelta: { fontSize: fonts.small, fontWeight: '700', marginTop: 2 },
});
