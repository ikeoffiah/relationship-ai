/// The Terms of Service and Privacy Policy, held in the app.
///
/// In the app rather than behind a link on purpose. The two links here pointed
/// at relationshipai.com/terms and /privacy — a code name, never the company —
/// so both were dead ends, and a policy nobody can open is not a policy.
/// Held locally they also work on a plane and cannot be quietly edited out from
/// under someone who agreed to a different version.
///
/// ── Before this ships ────────────────────────────────────────────────────────
///
/// **These are drafts and need a lawyer.** Not a disclaimer for politeness's
/// sake: this product handles what a regulator would treat as special-category
/// data about relationships and mental health, has a crisis-detection pathway,
/// accepts users who may be minors, and processes text through a US-based model
/// provider. GDPR Article 9, the UK equivalent, CCPA/CPRA, and the app-store
/// health-data rules all bear on it. A drafting error in that territory is not
/// a bug that surfaces in a test run.
///
/// Every placeholder below is a fact only you can supply — the legal entity,
/// its jurisdiction, the governing law, and the retention periods you intend to
/// actually honour. They are left visible rather than filled with plausible
/// text, because an invented company name in a contract is worse than a gap.
///
/// What is *not* guesswork is the substance. Everything the Privacy Policy says
/// about data flows was read off this codebase: the encryption key derivation,
/// which surfaces the partner can and cannot see, which text reaches the model,
/// what the behavioural profile records. If the implementation changes, this
/// file is wrong and has to change with it.
library;

/// Fill these in before publishing. Named rather than inlined so a search for
/// "[" finds every one of them.
/// Owjar is the company; "relationshipai" was only ever the project's code
/// name and should not appear in anything a user reads. The registered entity
/// name and its jurisdiction are still yours to supply — a trading name is not
/// the same as the party to a contract.
const String _entity = 'Owjar';
const String _registeredEntity = '[REGISTERED ENTITY NAME]';
const String _jurisdiction = '[JURISDICTION]';
const String _governingLaw = '[GOVERNING LAW]';
const String _contactEmail = 'support@owjar.co';
const String _effectiveDate = '[EFFECTIVE DATE]';

class LegalSection {
  final String heading;
  final String body;
  const LegalSection(this.heading, this.body);
}

class LegalDocument {
  final String title;
  final String effectiveDate;
  final String preamble;
  final List<LegalSection> sections;

  const LegalDocument({
    required this.title,
    required this.effectiveDate,
    required this.preamble,
    required this.sections,
  });
}

// ── Terms of Service ────────────────────────────────────────────────────────

const termsOfService = LegalDocument(
  title: 'Terms of Service',
  effectiveDate: _effectiveDate,
  preamble:
      'These terms are an agreement between you and $_entity about your use of '
      'Bliss. Please read the first two sections even if you read nothing '
      'else — they are the ones that affect your safety.',
  sections: [
    LegalSection(
      'Bliss is not therapy, and not an emergency service',
      'Bliss is a self-help tool that uses artificial intelligence to help two '
          'people communicate. It is not a licensed therapist, counsellor, '
          'psychologist or medical provider, and using it does not create a '
          'clinical relationship with anyone.\n\n'
          'Nothing Bliss says is a diagnosis, a treatment plan, or medical, '
          'legal or financial advice. It cannot examine you, it does not know '
          'your history beyond what you tell it, and it can be wrong.\n\n'
          'Bliss cannot respond to an emergency. If you or someone else is in '
          'danger, contact your local emergency number or a crisis line. The '
          'Support screen lists services and works without an account.\n\n'
          'If you are receiving care from a professional, Bliss is not a '
          'substitute for it and is not a reason to stop.',
    ),
    LegalSection(
      'If Bliss notices something concerning',
      'Bliss checks messages for signs that someone may be at risk, and may '
          'show you crisis resources or suggest professional support. This is '
          'an automated check made by software. It is not a clinical '
          'assessment, it will sometimes be wrong in both directions, and it is '
          'not monitoring you on anyone\'s behalf.\n\n'
          'It does not contact emergency services for you, and it does not '
          'alert your partner. Nobody is watching your conversation in real '
          'time. Do not rely on Bliss to raise an alarm.',
    ),
    LegalSection(
      'Who can use Bliss',
      'You need to be old enough to form a binding contract where you live, '
          'and at least 16. Some features are restricted further: intimate '
          'content requires that both partners have verified their age and both '
          'have opted in, and either of you can withdraw that at any time.\n\n'
          'If we learn that an account belongs to someone below the minimum '
          'age, we will close it and delete its data.',
    ),
    LegalSection(
      'Your account, and the two of you',
      'Keep your credentials to yourself, and use a passcode or biometric lock '
          'on your device — anyone holding an unlocked phone can read the '
          'conversation.\n\n'
          'Bliss is built for two people who both choose to be here. Connecting '
          'to a partner means you agree that the shared parts of the app are '
          'visible to them: your conversation, shared plans and calendar items, '
          'game answers once revealed, and progress on shared goals.\n\n'
          'Some things stay yours alone. Private sessions with Bliss, the '
          'private guidance it offers you about a difficult message, and what '
          'it has noticed about your own patterns are not shown to your '
          'partner. See the Privacy Policy for the full list.\n\n'
          'Either of you can end the connection at any time, without the '
          'other\'s agreement.',
    ),
    LegalSection(
      'Using Bliss fairly',
      'Do not use Bliss to threaten, harass, coerce, stalk or monitor anyone, '
          'including your partner. Do not use it to impersonate someone, to '
          'break the law, or to attempt to reach another couple\'s data.\n\n'
          'Do not use it to reach conclusions about a person and then present '
          'those conclusions as professional findings — in a legal proceeding, '
          'for example. It is not built for that and is not reliable for it.\n\n'
          'We may suspend or close an account that is being used this way.',
    ),
    LegalSection(
      'What you write stays yours',
      'You keep ownership of everything you write. You give us permission to '
          'store it, process it, and send the parts described in the Privacy '
          'Policy to the providers listed there, for the purpose of running the '
          'app for you. That permission ends when you delete the content or '
          'your account, except where we are required to keep something.\n\n'
          'We do not sell your content, and we do not use it to train other '
          'companies\' models.',
    ),
    LegalSection(
      'Paid features',
      'Some features may be paid. Prices, billing periods and renewal terms are '
          'shown before you pay. Subscriptions bought through an app store are '
          'billed and cancelled through that store, under its refund rules.\n\n'
          'If a paid feature stops working for a prolonged period, contact us '
          'at $_contactEmail.',
    ),
    LegalSection(
      'When things go wrong',
      'Bliss is provided as it is. We do not promise it will be available '
          'without interruption, that its suggestions will suit your situation, '
          'or that its automated checks will catch everything.\n\n'
          'To the extent the law allows, $_entity is not liable for indirect or '
          'consequential loss, and our total liability is limited to what you '
          'paid us in the twelve months before the claim.\n\n'
          'Nothing here limits liability that cannot be limited under '
          '$_jurisdiction law — including for death or personal injury caused '
          'by negligence, or for fraud.',
    ),
    LegalSection(
      'Ending it',
      'You can stop using Bliss and delete your account at any time from '
          'Settings. Deleting your account removes your personal data on the '
          'schedule in the Privacy Policy.\n\n'
          'Deleting your account does not delete your partner\'s copy of '
          'messages you sent them, in the same way that leaving a group chat '
          'does not unsend what you said.\n\n'
          'We may close an account for a serious or repeated breach of these '
          'terms, and will tell you why unless the law prevents us.',
    ),
    LegalSection(
      'Changes',
      'We will tell you in the app before a material change takes effect, and '
          'give you a reasonable chance to read it. Continuing to use Bliss '
          'after that means you accept the new terms; if you do not, you can '
          'delete your account.',
    ),
    LegalSection(
      'Law and disputes',
      'These terms are governed by $_governingLaw, and the courts of '
          '$_jurisdiction have jurisdiction. Nothing here removes a right you '
          'have as a consumer under the law where you live.\n\n'
          'Please write to $_contactEmail first. Most things are quicker to fix '
          'that way than through a court.',
    ),
  ],
);

// ── Privacy Policy ──────────────────────────────────────────────────────────

const privacyPolicy = LegalDocument(
  title: 'Privacy Policy',
  effectiveDate: _effectiveDate,
  preamble:
      'Bliss is built around a conversation between two people, which makes '
          'this policy unusually important. It sets out plainly what is stored, '
          'who can read it, and the one thing people most often assume about an '
          'app like this that is not true.',
  sections: [
    LegalSection(
      'Read this part first: Bliss can read your messages',
      'Your conversation is encrypted where it is stored. It is not '
          'end-to-end encrypted, and we want to be direct about that rather '
          'than let the word "encrypted" imply something stronger.\n\n'
          'The key is derived from your relationship, not from one person\'s '
          'device. That means both of you can read the thread on any device you '
          'sign in on — and it means Bliss can read it too. It has to, in order '
          'to suggest a rewrite, notice that a message may land badly, or '
          'answer when you tag it.\n\n'
          'This is a deliberate trade, not an oversight. An end-to-end '
          'encrypted product cannot coach a conversation it cannot see. If you '
          'would rather it did not, you can turn assistance off entirely in '
          'chat settings, and the thread will work as an ordinary chat.',
    ),
    LegalSection(
      'What we collect',
      'Things you give us: your email and name; your answers to the onboarding '
          'questionnaires about attachment and communication style; your '
          'messages, stickers and reactions; daily check-ins and answers; '
          'shared goals, plans and calendar items; game answers; anything you '
          'write in a session with Bliss.\n\n'
          'Things the app produces from use: how far each of you has read the '
          'thread and whether a message reached a device; whether you currently '
          'have the app open, which your partner sees as "Online"; observed '
          'tendencies in how you communicate (described below); points and '
          'activity counts; a tamper-evident log of security-relevant events '
          'such as sign-ins and consent changes.\n\n'
          'Things your device or the platform gives us: a push notification '
          'token; app version and device type; crash and error reports.\n\n'
          'We do not collect your location, your contacts, or your photo '
          'library.',
    ),
    LegalSection(
      'What your partner can and cannot see',
      'They can see: the shared conversation, including messages you have sent '
          'and whether you have read theirs; whether you are currently online; '
          'shared plans, calendar items and goals; your game answers once both '
          'of you have answered; that you are active in the app.\n\n'
          'They cannot see: your private sessions with Bliss, or that you had '
          'one; the private guidance Bliss offers you about a message they '
          'sent; what Bliss has observed about your own patterns; your '
          'questionnaire answers; when you were last online, which we do not '
          'record for display at all.\n\n'
          'That last one is deliberate. A timestamp of when someone was awake '
          'and did not reply is a different feature with a different cost, and '
          'it is the one that gets used against people. Presence is only ever '
          '"here now" or nothing.',
    ),
    LegalSection(
      'What Bliss learns from how you behave',
      'Alongside your questionnaire answers, Bliss records tendencies it can '
          'observe: that messages sometimes get paused before sending, that a '
          'repair gesture was sent, that a reply followed a long silence after '
          'a sharp exchange. This is how it gives advice that fits you rather '
          'than advice in general.\n\n'
          'Three limits are built in. It records behaviour, not labels — '
          '"tends to go quiet when things get sharp", never a clinical '
          'category. It fades: an observation loses half its weight every three '
          'weeks, so it describes how you have been lately rather than who you '
          'are. And it needs repetition before it counts for anything, so one '
          'difficult evening changes nothing.\n\n'
          'You can read what it has noticed about you. Your partner cannot — '
          'there is no way to ask for anyone else\'s.',
    ),
    LegalSection(
      'How we use it',
      'To run the features you are using; to generate suggestions, rewrites and '
          'session responses; to send reminders and notifications you have '
          'asked for; to check messages for signs of risk and offer support '
          'resources; to keep accounts secure and investigate abuse; to fix '
          'crashes; and to understand which features are used, in aggregate.\n\n'
          'We do not sell your data, we do not use it for advertising, and we '
          'do not use your conversations to train models — ours or anyone '
          'else\'s.',
    ),
    LegalSection(
      'Who else processes it',
      'OpenAI, in the United States, receives the message text needed for a '
          'suggestion, rewrite, safety check or session reply. Under its API '
          'terms this content is not used to train its models.\n\n'
          'Google Firebase delivers push notifications. Sentry receives crash '
          'and error reports. LiveKit carries audio and video calls, which are '
          'not recorded. Our servers and databases run with a cloud '
          'infrastructure provider.\n\n'
          'Each receives only what it needs for its part, under contract, and '
          'none of them may use your data for their own purposes. Some are '
          'outside your country; where that applies we rely on the standard '
          'contractual protections for international transfers.',
    ),
    LegalSection(
      'How long we keep it',
      'Your content stays while your account is open. Deleting your account '
          'starts deletion of your personal data within $_todoRetention.\n\n'
          'Two things outlast that. Messages you sent your partner remain in '
          'their copy of the conversation, as they would in any chat. And the '
          'security event log is kept for $_todoAuditRetention because its '
          'purpose is to show that nothing was altered after the fact — it '
          'records that an event happened, not what you said.\n\n'
          'Backups age out on their own schedule and are not searched for '
          'individual deletions.',
    ),
    LegalSection(
      'Your choices',
      'You can read and export your data, correct it, delete your account, '
          'withdraw a consent, or ask us to restrict how we use something. '
          'Assistance can be switched off in chat settings. Intimate content '
          'requires both of you to opt in and either of you can withdraw. '
          'Notifications can be turned off per type, or at the OS level.\n\n'
          'Write to $_contactEmail and we will respond within the period the '
          'law where you live requires. Depending on where that is, you may also '
          'have the right to complain to a data protection regulator.',
    ),
    LegalSection(
      'Security',
      'Message content is encrypted at rest. Connections use TLS. Access to '
          'production data is limited and logged, and security-relevant events '
          'are written to a hash-chained log so that later tampering is '
          'detectable.\n\n'
          'No system is perfectly secure, and the most likely way your '
          'conversation is read by someone you did not intend is an unlocked '
          'phone. Use a device passcode.',
    ),
    LegalSection(
      'Children',
      'Bliss is not for under-16s. Some features require verified age. If we '
          'find an account belonging to someone under the minimum age we close '
          'it and delete its data. If you believe a child is using Bliss, '
          'write to $_contactEmail.',
    ),
    LegalSection(
      'Changes to this policy',
      'If we change something material we will tell you in the app before it '
          'takes effect, and say what changed rather than only that something '
          'did.',
    ),
    LegalSection(
      'Contact',
      '$_entity ($_registeredEntity), $_jurisdiction.\n$_contactEmail.\nbliss is a product of owjar.co.',
    ),
  ],
);

/// Retention periods you have to decide and then honour. Deliberately not
/// pre-filled: "30 days" in a policy is a promise about infrastructure, and
/// writing a number here that the deletion job does not actually meet is worse
/// than admitting the number is not set.
const String _todoRetention = '[RETENTION PERIOD]';
const String _todoAuditRetention = '[AUDIT LOG RETENTION PERIOD]';
