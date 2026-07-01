import 'package:flutter/material.dart';
import 'package:mobile/shared/widgets/custom_toast.dart';

class ToastService {
  static void showSuccess(BuildContext context, String message) {
    if (!context.mounted) return;
    CustomToast.show(context, message, type: ToastType.success);
  }

  static void showError(BuildContext context, String message) {
    if (!context.mounted) return;
    CustomToast.show(context, message, type: ToastType.error);
  }

  static void showInfo(BuildContext context, String message) {
    if (!context.mounted) return;
    CustomToast.show(context, message, type: ToastType.info);
  }

  static void showWarning(BuildContext context, String message) {
    if (!context.mounted) return;
    // Assuming warning maps to info or we add a new type.
    // For now mapping to info, but ideally we add warning type.
    // Given the enum only had success, error, info.
    CustomToast.show(context, message, type: ToastType.info);
  }
}
