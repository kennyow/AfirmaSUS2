from django.test import SimpleTestCase
from core.views.utils import completar_datas_atividades, ordenar_atividades_timeline


class ActivityOrderTests(SimpleTestCase):
    def test_same_month_uses_exact_dates_from_dynamic_timeline(self):
        activities = [{'titulo': name, 'data': 'Novembro / 2026'} for name in
                      ('ENEX 2026', '3º Encontro Comunitário de Saúde', 'Encontro Nacional do Programa AFIRMASUS')]
        events = [{'text': {'headline': activity['titulo']},
                   'start_date': {'year': '2026', 'month': '11', 'day': str(day)}}
                  for activity, day in zip(activities, (3, 12, 17))]
        ordered = ordenar_atividades_timeline(completar_datas_atividades(activities, events))
        self.assertEqual([a['titulo'] for a in ordered], [activities[2]['titulo'], activities[1]['titulo'], activities[0]['titulo']])
        self.assertEqual([a['data'] for a in ordered], ['17/11/2026', '12/11/2026', '03/11/2026'])
        self.assertEqual(activities[0]['data'], 'Novembro / 2026')

    def test_preserves_explicit_dates_and_ambiguous_or_unmatched_months(self):
        activities = [{'titulo': 'Evento', 'data': '04/11/2026'}, {'titulo': 'Evento', 'data': 'Novembro / 2026'},
                      {'titulo': 'Sem correspondência', 'data': 'Novembro / 2026'}]
        events = [{'text': {'headline': 'Evento'}, 'start_date': {'year': '2026', 'month': '11', 'day': day}}
                  for day in ('3', '12')]
        self.assertEqual(completar_datas_atividades(activities, events), activities)
