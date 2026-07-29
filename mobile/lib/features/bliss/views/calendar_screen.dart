import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/features/bliss/bliss_models.dart';
import 'package:mobile/features/bliss/calendar_viewmodel.dart';
import 'package:mobile/shared/widgets/app_card.dart';
import 'package:mobile/shared/widgets/support_action.dart';

/// The couple's calendar.
///
/// A month grid with an agenda for the selected day underneath, rather than a
/// scrolling agenda alone: the question people bring to a shared calendar is
/// usually "are we free on the 14th", which a grid answers at a glance and a
/// list makes you scroll for.
///
/// Invitations waiting on this person sit *above* the grid. An unanswered
/// question should not depend on someone happening to tap the right day.
class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<CalendarViewModel>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<CalendarViewModel>(
      builder: (context, vm, _) {
        return Scaffold(
          backgroundColor: AppColors.creamWhite,
          appBar: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            title: Text(
              'Your calendar',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            actions: const [SupportAction()],
          ),
          body: SafeArea(
            top: false,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.xxl,
                AppSpacing.sm,
                AppSpacing.xxl,
                AppSpacing.xxxl,
              ),
              children: [
                for (final invite in vm.pendingInvites) ...[
                  _InviteCard(item: invite, vm: vm),
                  const SizedBox(height: AppSpacing.md),
                ],
                _MonthHeader(vm: vm),
                const SizedBox(height: AppSpacing.md),
                _MonthGrid(vm: vm),
                const SizedBox(height: AppSpacing.xl),
                _Agenda(vm: vm),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _MonthHeader extends StatelessWidget {
  final CalendarViewModel vm;
  const _MonthHeader({required this.vm});

  static const _months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          key: const Key('calendar_prev_month'),
          onPressed: () => vm.stepMonth(-1),
          icon: const Icon(Icons.chevron_left_rounded),
          tooltip: 'Previous month',
        ),
        Expanded(
          child: Text(
            '${_months[vm.month.month - 1]} ${vm.month.year}',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
        IconButton(
          key: const Key('calendar_next_month'),
          onPressed: () => vm.stepMonth(1),
          icon: const Icon(Icons.chevron_right_rounded),
          tooltip: 'Next month',
        ),
      ],
    );
  }
}

class _MonthGrid extends StatelessWidget {
  final CalendarViewModel vm;
  const _MonthGrid({required this.vm});

  @override
  Widget build(BuildContext context) {
    final first = DateTime(vm.month.year, vm.month.month, 1);
    // Monday-first. DateTime.weekday is 1=Mon..7=Sun, so this is already the
    // offset we want without any juggling.
    final leading = first.weekday - 1;
    final daysInMonth = DateTime(vm.month.year, vm.month.month + 1, 0).day;
    final today = CalendarViewModel.dayOf(DateTime.now());

    return Column(
      children: [
        Row(
          children: [
            for (final label in const ['M', 'T', 'W', 'T', 'F', 'S', 'S'])
              Expanded(
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: AppColors.softCharcoal.withValues(alpha: 0.45),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            childAspectRatio: 1,
          ),
          itemCount: leading + daysInMonth,
          itemBuilder: (context, index) {
            if (index < leading) return const SizedBox.shrink();
            final day = DateTime(
              vm.month.year,
              vm.month.month,
              index - leading + 1,
            );
            return _DayCell(
              day: day,
              vm: vm,
              isToday: day == today,
              isSelected: day == vm.selectedDay,
            );
          },
        ),
      ],
    );
  }
}

class _DayCell extends StatelessWidget {
  final DateTime day;
  final CalendarViewModel vm;
  final bool isToday;
  final bool isSelected;

  const _DayCell({
    required this.day,
    required this.vm,
    required this.isToday,
    required this.isSelected,
  });

  @override
  Widget build(BuildContext context) {
    final has = vm.hasAnythingOn(day);
    final asks = vm.needsMyAnswerOn(day);

    return Semantics(
      button: true,
      selected: isSelected,
      label:
          '${day.day} ${has ? '— something on' : '— nothing on'}'
          '${asks ? ', waiting on your answer' : ''}',
      child: InkWell(
        key: Key('calendar_day_${day.day}'),
        borderRadius: BorderRadius.circular(AppRadii.sm),
        onTap: () => vm.select(day),
        child: Container(
          margin: const EdgeInsets.all(2),
          decoration: BoxDecoration(
            color: isSelected
                ? AppColors.warmCoral.withValues(alpha: 0.16)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadii.sm),
            border: isToday
                ? Border.all(color: AppColors.warmCoral.withValues(alpha: 0.5))
                : null,
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${day.day}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
              const SizedBox(height: 2),
              // A dot, not a count. The number of things on a day is not
              // information anyone acts on from a grid, and a "3" reads as
              // busyness to be anxious about.
              SizedBox(
                height: 5,
                child: has
                    ? Container(
                        width: 5,
                        height: 5,
                        decoration: BoxDecoration(
                          // An unanswered invitation is the one thing on this
                          // screen worth a different colour.
                          color: asks
                              ? AppColors.categoryPlum
                              : AppColors.warmCoral,
                          shape: BoxShape.circle,
                        ),
                      )
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Agenda extends StatelessWidget {
  final CalendarViewModel vm;
  const _Agenda({required this.vm});

  @override
  Widget build(BuildContext context) {
    final items = vm.selectedItems;
    if (vm.isLoading && items.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.xl),
          child: CircularProgressIndicator(color: AppColors.warmCoral),
        ),
      );
    }
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xl),
        child: Text(
          'Nothing on this day.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      );
    }
    return Column(
      children: [
        for (final item in items) ...[
          _AgendaRow(item: item, vm: vm),
          const SizedBox(height: AppSpacing.sm),
        ],
      ],
    );
  }
}

class _AgendaRow extends StatelessWidget {
  final BlissItem item;
  final CalendarViewModel vm;
  const _AgendaRow({required this.item, required this.vm});

  @override
  Widget build(BuildContext context) {
    if (item.awaitingMyAnswer) return _InviteCard(item: item, vm: vm);

    final status = item.inviteStatusLabel;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          Text(
            _time(item.dueAt),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: AppColors.softCharcoal.withValues(alpha: 0.6),
              // Times in a column only line up with tabular figures.
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(width: AppSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.title, style: Theme.of(context).textTheme.bodyLarge),
                if (status != null)
                  Text(
                    status,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: item.partnerInvite == PartnerInvite.declined
                          ? AppColors.softCharcoal.withValues(alpha: 0.5)
                          : AppColors.seenTick,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _time(DateTime? at) {
    if (at == null) return '--:--';
    final local = at.toLocal();
    return '${local.hour.toString().padLeft(2, '0')}:'
        '${local.minute.toString().padLeft(2, '0')}';
  }
}

/// "Sam asked you to something." Accept or decline, nothing else.
class _InviteCard extends StatelessWidget {
  final BlissItem item;
  final CalendarViewModel vm;
  const _InviteCard({required this.item, required this.vm});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      key: Key('invite_${item.id}'),
      borderColor: AppColors.categoryPlum.withValues(alpha: 0.4),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'They asked you to this',
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: AppColors.categoryPlum),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(item.title, style: Theme.of(context).textTheme.titleMedium),
          if (item.dueAt != null)
            Text(
              _when(item.dueAt!),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  key: Key('invite_accept_${item.id}'),
                  onPressed: () => vm.respond(item, accept: true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warmCoral,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadii.md),
                    ),
                  ),
                  child: const Text("I'm in"),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: OutlinedButton(
                  key: Key('invite_decline_${item.id}'),
                  onPressed: () => vm.respond(item, accept: false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.softCharcoal,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadii.md),
                    ),
                  ),
                  // Not "Decline" — this is a partner asking, not a meeting
                  // request, and saying no to a Tuesday is not saying no to
                  // them.
                  child: const Text('Not this time'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static String _when(DateTime at) {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    final l = at.toLocal();
    final hour = l.hour % 12 == 0 ? 12 : l.hour % 12;
    final suffix = l.hour < 12 ? 'am' : 'pm';
    return '${days[l.weekday - 1]} ${l.day} ${months[l.month - 1]}, '
        '$hour:${l.minute.toString().padLeft(2, '0')}$suffix';
  }
}
