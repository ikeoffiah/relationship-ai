// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(ChatNotifier)
final chatProvider = ChatNotifierFamily._();

final class ChatNotifierProvider
    extends $NotifierProvider<ChatNotifier, ChatState> {
  ChatNotifierProvider._({
    required ChatNotifierFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'chatProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$chatNotifierHash();

  @override
  String toString() {
    return r'chatProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  ChatNotifier create() => ChatNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ChatState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ChatState>(value),
    );
  }

  @override
  bool operator ==(Object other) {
    return other is ChatNotifierProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$chatNotifierHash() => r'578c741db6ec6d7c108e8fc4b3f6fc8c1552f3c6';

final class ChatNotifierFamily extends $Family
    with
        $ClassFamilyOverride<
          ChatNotifier,
          ChatState,
          ChatState,
          ChatState,
          String
        > {
  ChatNotifierFamily._()
    : super(
        retry: null,
        name: r'chatProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  ChatNotifierProvider call(String sessionId) =>
      ChatNotifierProvider._(argument: sessionId, from: this);

  @override
  String toString() => r'chatProvider';
}

abstract class _$ChatNotifier extends $Notifier<ChatState> {
  late final _$args = ref.$arg as String;
  String get sessionId => _$args;

  ChatState build(String sessionId);
  @$mustCallSuper
  @override
  WhenComplete runBuild() {
    final ref = this.ref as $Ref<ChatState, ChatState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ChatState, ChatState>,
              ChatState,
              Object?,
              Object?
            >;
    return element.handleCreate(ref, () => build(_$args));
  }
}
