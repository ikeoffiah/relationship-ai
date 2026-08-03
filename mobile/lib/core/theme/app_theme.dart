import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/core/theme/app_dimens.dart';
import 'package:mobile/core/theme/app_motion.dart';

/// App theme configuration
/// Implements gentle, human-centered design principles
class AppTheme {
  // ── Motion ────────────────────────────────────────────────────────────────
  // These three have never been referenced by anything. They are kept only so
  // nothing breaks, and forwarded to `AppMotion`, which is where the vocabulary
  // now lives and which also handles the reduced-motion preference this app
  // has never honoured. Delete these once nothing points at them.

  @Deprecated('Use AppMotion.reveal, and AppMotion.duration() to honour reduced motion.')
  static const Duration slowFade = AppMotion.reveal;

  @Deprecated('Use AppMotion.settle, and AppMotion.duration() to honour reduced motion.')
  static const Duration gentleMotion = AppMotion.settle;

  @Deprecated('Use AppMotion.ambient, and check AppMotion.allowAmbient() before repeating.')
  static const Duration orbAnimation = AppMotion.ambient;

  // Typography - rounded, human sans-serif
  static TextTheme get textTheme {
    return TextTheme(
      // Headings - rounded, gentle
      displayLarge: GoogleFonts.inter(
        fontSize: 32,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.5,
        color: AppColors.softCharcoal,
      ),
      displayMedium: GoogleFonts.inter(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.5,
        color: AppColors.softCharcoal,
      ),
      displaySmall: GoogleFonts.inter(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
        color: AppColors.softCharcoal,
      ),

      // Body text - highly readable, gentle line spacing
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.6,
        letterSpacing: 0.15,
        color: AppColors.softCharcoal,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.6,
        letterSpacing: 0.25,
        color: AppColors.softCharcoal,
      ),
      /// Captions, timestamps, helper text.
      ///
      /// **Colour corrected 2026-08-03.** This was
      /// `softCharcoal.withValues(alpha: 0.7)`, which composites to `#807F7D`
      /// over cream — **3.88:1**, below the 4.5:1 AA floor, at the 12px size
      /// that is the whole reason this slot exists. It was the single
      /// most-inherited accessibility failure in the app, since every screen
      /// that reached for `bodySmall` inherited it silently. [AppColors.mutedInk]
      /// is the same visual intent measured properly: 5.12:1, and warm rather
      /// than the grey a transparency wash produces.
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.5,
        letterSpacing: 0.4,
        color: AppColors.mutedInk,
      ),
      headlineSmall: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
        color: AppColors.softCharcoal,
      ),

      // ── The two missing rungs ───────────────────────────────────────────
      // 18px and 22px are the two most-hardcoded sizes in the app after 16 —
      // 22 inline uses of `fontSize: 18` and 10 of `fontSize: 22` — and
      // neither had a slot, so both were invented at every call site with
      // whatever weight and colour the author felt like. Filling them
      // completes the ladder: 11 · 12 · 14 · 15 · 16 · 18 · 20 · 22 · 24 ·
      // 28 · 32.

      /// Section headings inside a screen; the largest thing on a card.
      headlineLarge: GoogleFonts.inter(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
        color: AppColors.softCharcoal,
      ),

      /// Sub-section headings, and the prominent line in a hero card.
      headlineMedium: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
        color: AppColors.softCharcoal,
      ),

      // ── Title & label slots ─────────────────────────────────────────────
      // Added so the inner app can stop hardcoding TextStyle(fontSize: …).
      // Only 7 of Material's 15 slots were defined, so screens that needed a
      // "card title" or "button label" invented one inline — dozens of times,
      // at drifting sizes. The styles above are deliberately untouched: the
      // onboarding flow reads from them and must render exactly as it does now.

      /// Screen and app-bar titles.
      titleLarge: GoogleFonts.inter(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
        color: AppColors.softCharcoal,
      ),

      /// Card titles — the most repeated inline literal in the inner app.
      titleMedium: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.15,
        color: AppColors.softCharcoal,
      ),

      /// List-row and compact card titles.
      titleSmall: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.1,
        color: AppColors.softCharcoal,
      ),

      /// Button labels.
      labelLarge: GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        letterSpacing: 0,
        color: AppColors.softCharcoal,
      ),

      /// Uppercase eyebrow labels above a section or card.
      labelMedium: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.8,
        color: AppColors.softCharcoal,
      ),

      /// Smallest supporting label (counts, timestamps, units).
      labelSmall: GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.5,
        color: AppColors.softCharcoal,
      ),
    );
  }

  // Light theme
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,

      // ── Colour scheme ───────────────────────────────────────────────────
      // Six roles were set and the other twenty were left to Material 3's
      // baseline, which is a *purple* scheme. Every unset role therefore
      // resolves to a lavender-tinted grey from a design system that is not
      // ours, and any widget touching one imports it into a cream app. That
      // is not hypothetical: `assistant_message_bubble.dart` reads
      // `surfaceContainerHighest`, so the counsellor's reply — the surface
      // this product charges $39 for — currently renders on `#E6E0E9`.
      //
      // All the container and outline roles are now bound to palette values.
      // A screen reaching for an M3 role can no longer leave the palette by
      // accident.
      colorScheme: const ColorScheme.light(
        primary: AppColors.warmCoral,
        // Was `Colors.white`, at **2.04:1**. See [AppColors.onBrand]: coral is
        // a fill, and a fill in this palette cannot carry white.
        onPrimary: AppColors.onBrand,
        primaryContainer: AppColors.rosePeach,
        onPrimaryContainer: AppColors.onBrand,

        secondary: AppColors.calmTeal,
        // Was `Colors.white`, at 2.14:1.
        onSecondary: AppColors.onBrand,
        secondaryContainer: AppColors.calmSurface,
        onSecondaryContainer: AppColors.softCharcoal,

        tertiary: AppColors.goldMedium,
        onTertiary: AppColors.onBrand,
        tertiaryContainer: AppColors.noticeSurface,
        onTertiaryContainer: AppColors.noticeInk,

        surface: AppColors.creamWhite,
        onSurface: AppColors.softCharcoal,
        onSurfaceVariant: AppColors.mutedInk,
        surfaceContainerLowest: Colors.white,
        surfaceContainerLow: AppColors.creamWhite,
        surfaceContainer: AppColors.neutralSurface,
        surfaceContainerHigh: AppColors.neutralSurface,
        surfaceContainerHighest: AppColors.assistantSurface,

        outline: AppColors.borderStrong,
        outlineVariant: AppColors.hairline,

        // The error *role* is the pale rose used for form validation, which is
        // deliberately not the crisis red — `AppColors.crisis` stays reserved
        // for the support screen and is never reachable through the theme.
        // Note that `error` itself is a fill (2.26:1 on cream), so error
        // *text* takes `onErrorContainer`, never `error`.
        error: AppColors.error,
        onError: AppColors.onBrand,
        errorContainer: Color(0xFFFDECEC),
        onErrorContainer: Color(0xFF9A2A2A),

        shadow: AppColors.onBrand,
        scrim: AppColors.onBrand,
      ),

      textTheme: textTheme,
      scaffoldBackgroundColor: AppColors.creamWhite,
      dividerColor: AppColors.hairline,

      // Cards are drawn by `AppCard` at `AppRadii.card` (20). This theme only
      // catches raw `Card()` widgets, of which there are eight — all of which
      // should become `AppCard`. Matching the radius here means they at least
      // stop being visibly a third shape while that happens.
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.card),
          side: const BorderSide(color: AppColors.hairline),
        ),
      ),

      // ── Component defaults ──────────────────────────────────────────────
      // These exist so that a screen written next week is on-system without
      // its author having to know anything. Every one of them encodes a rule
      // that is currently reimplemented by hand at dozens of call sites.

      appBarTheme: const AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: AppColors.creamWhite,
        surfaceTintColor: Colors.transparent,
        foregroundColor: AppColors.softCharcoal,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.3,
          color: AppColors.softCharcoal,
        ),
      ),

      iconTheme: const IconThemeData(
        size: AppIconSize.md,
        color: AppColors.softCharcoal,
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.warmCoral,
          foregroundColor: AppColors.onBrand,
          disabledBackgroundColor: AppColors.neutralSurface,
          disabledForegroundColor: AppColors.disabledInk,
          elevation: 0,
          minimumSize: const Size(0, AppTouch.min),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.xxl,
            vertical: AppSpacing.md,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.lg),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.softCharcoal,
          minimumSize: const Size(0, AppTouch.min),
          side: const BorderSide(
            color: AppColors.borderStrong,
            width: AppStroke.edge,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.lg),
          ),
        ),
      ),

      // Text buttons take charcoal, **not coral**. Coral text on cream is
      // 1.98:1 and is the most common single contrast failure left in the app
      // once the fills are fixed. A text button is identified by its position
      // and its label, not by being pink.
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.softCharcoal,
          minimumSize: const Size(0, AppTouch.min),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // `padded` is the default and is being restated deliberately: it is what
      // guarantees the 48pt minimum around an icon drawn at 20.
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppColors.softCharcoal,
          minimumSize: const Size(AppTouch.min, AppTouch.min),
          tapTargetSize: MaterialTapTargetSize.padded,
        ),
      ),

      chipTheme: ChipThemeData(
        backgroundColor: Colors.white,
        selectedColor: AppColors.warmCoral,
        disabledColor: AppColors.neutralSurface,
        side: const BorderSide(
          color: AppColors.borderStrong,
          width: AppStroke.hairline,
        ),
        labelStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: AppColors.softCharcoal,
        ),
        secondaryLabelStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: AppColors.onBrand,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
        showCheckmark: false,
      ),

      // `labelText`, not `hintText`. A placeholder that disappears the moment
      // someone types is not a label — it leaves the field unnamed for a
      // screen reader and unrecoverable for anyone who looks away mid-entry.
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.lg,
        ),
        labelStyle: const TextStyle(color: AppColors.mutedInk),
        hintStyle: const TextStyle(color: AppColors.mutedInk),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
          borderSide: const BorderSide(
            color: AppColors.borderStrong,
            width: AppStroke.edge,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
          borderSide: const BorderSide(
            color: AppColors.borderStrong,
            width: AppStroke.edge,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
          borderSide: const BorderSide(
            color: AppColors.focusRing,
            width: AppStroke.focus,
          ),
        ),
        errorStyle: const TextStyle(color: Color(0xFF9A2A2A)),
      ),

      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.creamWhite,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        showDragHandle: true,
        dragHandleColor: AppColors.borderStrong,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadii.lg),
          ),
        ),
      ),

      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.creamWhite,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.lg),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.onBrand,
        contentTextStyle: const TextStyle(color: AppColors.creamWhite),
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
      ),

      dividerTheme: const DividerThemeData(
        color: AppColors.hairline,
        thickness: AppStroke.hairline,
        space: AppSpacing.lg,
      ),

      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.warmCoral,
        linearTrackColor: AppColors.neutralSurface,
        circularTrackColor: AppColors.neutralSurface,
      ),
    );
  }
}
