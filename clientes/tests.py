from django.test import SimpleTestCase, override_settings


@override_settings(ALLOWED_HOSTS=['testserver'])
class GreetingViewsTests(SimpleTestCase):
    def test_homepage_displays_greeting(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>Hola mundo</h1>', html=True)
        self.assertContains(response, '<p>Bienvenidos a Progra III</p>', html=True)

    def test_saludo_displays_greeting(self):
        response = self.client.get('/saludo/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hola mundo, bienvenidos a progra lll')

    def test_saludo_nombre_includes_name_and_age(self):
        response = self.client.get('/saludo/Miguel/20/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'hola Miguel, tienes 20 años, bienvenidos a progra lll'
        )
