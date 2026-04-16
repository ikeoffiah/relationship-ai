import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/consent/models/consent_model.dart';

void main() {
  group('ConsentDisplayLabels', () {
    test('Correct human-readable strings shown for each consent state', () {
      expect(ConsentModel.labelFor('per_session'), 'Not saved after session ends');
      expect(ConsentModel.labelFor('30_days'), 'Saved for 30 days');
      expect(ConsentModel.labelFor('1_year'), 'Saved for 1 year');
      expect(ConsentModel.labelFor('indefinite'), 'Saved indefinitely');
      
      expect(ConsentModel.labelFor('never'), 'Not shared with partner');
      expect(ConsentModel.labelFor('anonymized'), 'Shared anonymously');
      expect(ConsentModel.labelFor('named'), 'Shared with your name');
      
      expect(ConsentModel.labelFor('not_enrolled'), 'Joint sessions off');
      expect(ConsentModel.labelFor('enrolled'), 'Joint sessions on');
      
      expect(ConsentModel.labelFor('not_participating'), 'No shared context');
      expect(ConsentModel.labelFor('read_only'), 'Partner can see summary');
      expect(ConsentModel.labelFor('read_write'), 'Both partners share context');
    });

    test('labelFor returns input if no mapping exists', () {
      expect(ConsentModel.labelFor('unknown_state'), 'unknown_state');
    });
  });
}
