import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/api_services/joint_session_api_service.dart';
import '../../core/theme/app_colors.dart';

/// Peer-to-peer video call for a joint session, backed by LiveKit. Fetches a
/// room token from the backend, connects, and shows the partner full-screen
/// with the user's own camera as a small picture-in-picture.
class JointVideoCallScreen extends StatefulWidget {
  final String sessionId;
  final String partnerName;

  const JointVideoCallScreen({
    super.key,
    required this.sessionId,
    this.partnerName = 'Your partner',
  });

  @override
  State<JointVideoCallScreen> createState() => _JointVideoCallScreenState();
}

class _JointVideoCallScreenState extends State<JointVideoCallScreen> {
  final _api = JointSessionApiService();
  Room? _room;

  bool _connecting = true;
  String? _error;
  bool _micOn = true;
  bool _camOn = true;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  Future<void> _connect() async {
    try {
      final statuses = await [Permission.camera, Permission.microphone].request();
      if (statuses[Permission.camera]?.isGranted != true ||
          statuses[Permission.microphone]?.isGranted != true) {
        setState(() {
          _connecting = false;
          _error = 'Camera and microphone access are needed for a video call.';
        });
        return;
      }

      final creds = await _api.fetchVideoToken(widget.sessionId);
      final room = Room();
      room.addListener(_onRoomChanged);
      await room.connect(creds['url'] as String, creds['token'] as String);
      await room.localParticipant?.setCameraEnabled(true);
      await room.localParticipant?.setMicrophoneEnabled(true);
      if (!mounted) {
        await room.disconnect();
        return;
      }
      setState(() {
        _room = room;
        _connecting = false;
      });
    } catch (e) {
      setState(() {
        _connecting = false;
        _error = _friendlyError(e);
      });
    }
  }

  String _friendlyError(Object e) {
    final msg = e.toString();
    if (msg.contains('503') || msg.contains('video_unconfigured')) {
      return 'Video calling isn\'t available yet. Please try again later.';
    }
    return 'Couldn\'t start the video call. Please try again.';
  }

  void _onRoomChanged() {
    if (mounted) setState(() {});
  }

  VideoTrack? get _remoteVideo {
    final room = _room;
    if (room == null) return null;
    for (final participant in room.remoteParticipants.values) {
      for (final pub in participant.videoTrackPublications) {
        if (pub.subscribed && pub.track != null) return pub.track as VideoTrack;
      }
    }
    return null;
  }

  VideoTrack? get _localVideo {
    final pubs = _room?.localParticipant?.videoTrackPublications;
    if (pubs == null) return null;
    for (final pub in pubs) {
      if (pub.track != null) return pub.track as VideoTrack;
    }
    return null;
  }

  Future<void> _toggleMic() async {
    final next = !_micOn;
    await _room?.localParticipant?.setMicrophoneEnabled(next);
    setState(() => _micOn = next);
  }

  Future<void> _toggleCam() async {
    final next = !_camOn;
    await _room?.localParticipant?.setCameraEnabled(next);
    setState(() => _camOn = next);
  }

  Future<void> _hangUp() async {
    await _room?.disconnect();
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _room?.removeListener(_onRoomChanged);
    _room?.disconnect();
    _room?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: _connecting
            ? _status('Connecting you two…', spinner: true)
            : _error != null
                ? _status(_error!, spinner: false)
                : _callView(),
      ),
    );
  }

  Widget _status(String message, {required bool spinner}) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (spinner)
                const CircularProgressIndicator(color: AppColors.warmCoral)
              else
                const Text('📵', style: TextStyle(fontSize: 44)),
              const SizedBox(height: 20),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 16),
              ),
              if (!spinner) ...[
                const SizedBox(height: 24),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Back', style: TextStyle(color: AppColors.warmCoral)),
                ),
              ],
            ],
          ),
        ),
      );

  Widget _callView() {
    final remote = _remoteVideo;
    final local = _localVideo;
    return Stack(
      children: [
        // Partner, full-screen (or a waiting state until they join).
        Positioned.fill(
          child: remote != null
              ? VideoTrackRenderer(remote, fit: VideoViewFit.cover)
              : Container(
                  color: const Color(0xFF1A1A1A),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(color: AppColors.calmTeal),
                        const SizedBox(height: 16),
                        Text(
                          'Waiting for ${widget.partnerName} to join…',
                          style: const TextStyle(color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                ),
        ),
        // Own camera, small picture-in-picture.
        Positioned(
          top: 16,
          right: 16,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              width: 110,
              height: 160,
              child: (local != null && _camOn)
                  ? VideoTrackRenderer(local, fit: VideoViewFit.cover)
                  : Container(
                      color: const Color(0xFF2A2A2A),
                      child: const Center(
                        child: Icon(Icons.videocam_off, color: Colors.white54),
                      ),
                    ),
            ),
          ),
        ),
        // Controls.
        Positioned(
          left: 0,
          right: 0,
          bottom: 32,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _control(
                icon: _micOn ? Icons.mic : Icons.mic_off,
                active: _micOn,
                onTap: _toggleMic,
              ),
              const SizedBox(width: 20),
              _control(
                icon: Icons.call_end,
                background: AppColors.error,
                onTap: _hangUp,
              ),
              const SizedBox(width: 20),
              _control(
                icon: _camOn ? Icons.videocam : Icons.videocam_off,
                active: _camOn,
                onTap: _toggleCam,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _control({
    required IconData icon,
    required VoidCallback onTap,
    bool active = true,
    Color? background,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: background ?? (active ? Colors.white24 : Colors.white10),
        ),
        child: Icon(icon, color: Colors.white, size: 26),
      ),
    );
  }
}
