# This file is part of wger Workout Manager.
#
# wger Workout Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wger Workout Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Workout Manager.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import datetime
import json
from decimal import Decimal

# Django
from django.core.exceptions import ValidationError
from django.urls import reverse

# wger
from wger.core.models import Language
from wger.core.tests import api_base_test
from wger.core.tests.base_testcase import (
    WgerAddTestCase,
    WgerDeleteTestCase,
    WgerEditTestCase,
    WgerTestCase,
)
from wger.nutrition.models import (
    Ingredient,
    Meal,
)
from wger.utils.constants import NUTRITION_TAB


class IngredientRepresentationTestCase(WgerTestCase):
    """
    Test the representation of a model
    """

    def test_representation(self):
        """
        Test that the representation of an object is correct
        """
        self.assertEqual("{0}".format(Ingredient.objects.get(pk=1)), 'Test ingredient 1')


class DeleteIngredientTestCase(WgerDeleteTestCase):
    """
    Tests deleting an ingredient
    """

    object_class = Ingredient
    url = 'nutrition:ingredient:delete'
    pk = 1


class EditIngredientTestCase(WgerEditTestCase):
    """
    Tests editing an ingredient
    """

    object_class = Ingredient
    url = 'nutrition:ingredient:edit'
    pk = 1
    data = {
        'name': 'A new name',
        'sodium': 2,
        'energy': 200,
        'fat': 10,
        'carbohydrates_sugar': 5,
        'fat_saturated': 3.14,
        'fibres': 2.1,
        'protein': 20,
        'carbohydrates': 10,
        'license': 2,
        'license_author': 'me!'
    }

    def post_test_hook(self):
        """
        Test that the update date is correctly set
        """
        if self.current_user == 'admin':
            ingredient = Ingredient.objects.get(pk=1)
            self.assertEqual(ingredient.update_date, datetime.date.today())


class AddIngredientTestCase(WgerAddTestCase):
    """
    Tests adding an ingredient
    """

    object_class = Ingredient
    url = 'nutrition:ingredient:add'
    user_fail = False
    data = {
        'name': 'A new ingredient',
        'sodium': 2,
        'energy': 200,
        'fat': 10,
        'carbohydrates_sugar': 5,
        'fat_saturated': 3.14,
        'fibres': 2.1,
        'protein': 20,
        'carbohydrates': 10,
        'license': 2,
        'license_author': 'me!'
    }

    def post_test_hook(self):
        """
        Test that the creation date and the status are correctly set
        """
        if self.current_user == 'admin':
            ingredient = Ingredient.objects.get(pk=self.pk_after)
            self.assertEqual(ingredient.creation_date, datetime.date.today())
            self.assertEqual(ingredient.status, Ingredient.STATUS_ACCEPTED)
        elif self.current_user == 'test':
            ingredient = Ingredient.objects.get(pk=self.pk_after)
            self.assertEqual(ingredient.status, Ingredient.STATUS_PENDING)


class IngredientNameShortTestCase(WgerTestCase):
    """
    Tests that ingredient cannot have name with length less than 3
    """
    data = {
        'name': 'Ui',
        'sodium': 2,
        'energy': 200,
        'fat': 10,
        'carbohydrates_sugar': 5,
        'fat_saturated': 3.14,
        'fibres': 2.1,
        'protein': 20,
        'carbohydrates': 10,
        'license': 2,
        'license_author': 'me!'
    }

    def test_add_ingredient_short_name(self):
        """
        Test that ingredient cannot be added with name of length less than 3
        """
        self.user_login('admin')

        count_before = Ingredient.objects.count()

        response = self.client.post(reverse('nutrition:ingredient:add'), self.data)
        count_after = Ingredient.objects.count()
        self.assertEqual(response.status_code, 200)

        # Ingredient was not added
        self.assertEqual(count_before, count_after)

    def test_edit_ingredient_short_name(self):
        """
        Test that ingredient cannot be edited to name of length less than 3
        """
        self.user_login('admin')

        response = self.client.post(
            reverse('nutrition:ingredient:edit', kwargs={'pk': '1'}), self.data
        )
        self.assertEqual(response.status_code, 200)

        ingredient = Ingredient.objects.get(pk=1)
        # Ingredient was not edited
        self.assertNotEqual(ingredient.update_date, datetime.date.today())


class IngredientDetailTestCase(WgerTestCase):
    """
    Tests the ingredient details page
    """

    def ingredient_detail(self, editor=False):
        """
        Tests the ingredient details page
        """

        response = self.client.get(reverse('nutrition:ingredient:view', kwargs={'pk': 6}))
        self.assertEqual(response.status_code, 200)

        # Correct tab is selected
        self.assertEqual(response.context['active_tab'], NUTRITION_TAB)
        self.assertTrue(response.context['ingredient'])

        # Only authorized users see the edit links
        if editor:
            self.assertContains(response, 'Edit ingredient')
            self.assertContains(response, 'Delete ingredient')
            self.assertContains(response, 'pending review')
        else:
            self.assertNotContains(response, 'Edit ingredient')
            self.assertNotContains(response, 'Delete ingredient')
            self.assertNotContains(response, 'pending review')

        # Non-existent ingredients throw a 404.
        response = self.client.get(reverse('nutrition:ingredient:view', kwargs={'pk': 42}))
        self.assertEqual(response.status_code, 404)

    def test_ingredient_detail_editor(self):
        """
        Tests the ingredient details page as a logged-in user with editor rights
        """

        self.user_login('admin')
        self.ingredient_detail(editor=True)

    def test_ingredient_detail_non_editor(self):
        """
        Tests the ingredient details page as a logged-in user without editor rights
        """

        self.user_login('test')
        self.ingredient_detail(editor=False)

    def test_ingredient_detail_logged_out(self):
        """
        Tests the ingredient details page as an anonymous (logged out) user
        """

        self.ingredient_detail(editor=False)


class IngredientSearchTestCase(WgerTestCase):
    """
    Tests the ingredient search functions
    """

    def search_ingredient(self, fail=True):
        """
        Helper function
        """

        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        response = self.client.get(reverse('ingredient-search'), {'term': 'test'}, **kwargs)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf8'))
        self.assertEqual(len(result['suggestions']), 2)
        self.assertEqual(result['suggestions'][0]['value'], 'Ingredient, test, 2, organic, raw')
        self.assertEqual(result['suggestions'][0]['data']['id'], 2)
        suggestion_0_name = 'Ingredient, test, 2, organic, raw'
        self.assertEqual(result['suggestions'][0]['data']['name'], suggestion_0_name)
        self.assertEqual(result['suggestions'][0]['data']['image'], None)
        self.assertEqual(result['suggestions'][0]['data']['image_thumbnail'], None)
        self.assertEqual(result['suggestions'][1]['value'], 'Test ingredient 1')
        self.assertEqual(result['suggestions'][1]['data']['id'], 1)
        self.assertEqual(result['suggestions'][1]['data']['name'], 'Test ingredient 1')
        self.assertEqual(result['suggestions'][1]['data']['image'], None)
        self.assertEqual(result['suggestions'][1]['data']['image_thumbnail'], None)

        # Search for an ingredient pending review (0 hits, "Pending ingredient")
        response = self.client.get(reverse('ingredient-search'), {'term': 'Pending'}, **kwargs)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf8'))
        self.assertEqual(len(result['suggestions']), 0)

    def test_search_ingredient_anonymous(self):
        """
        Test searching for an ingredient by an anonymous user
        """

        self.search_ingredient()

    def test_search_ingredient_logged_in(self):
        """
        Test searching for an ingredient by a logged-in user
        """

        self.user_login('test')
        self.search_ingredient()


class IngredientValuesTestCase(WgerTestCase):
    """
    Tests the nutritional value calculator for an ingredient
    """

    def calculate_value(self):
        """
        Helper function
        """

        # Get the nutritional values in 1 gram of product
        response = self.client.get(
            reverse('api-ingredient-get-values', kwargs={'pk': 1}), {
                'amount': 1,
                'ingredient': 1,
                'unit': ''
            }
        )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf8'))
        self.assertEqual(len(result), 9)
        self.assertEqual(
            result, {
                'sodium': '0.01',
                'energy': '1.76',
                'energy_kilojoule': '7.36',
                'fat': '0.08',
                'carbohydrates_sugar': '0.00',
                'fat_saturated': '0.03',
                'fibres': '0.00',
                'protein': '0.26',
                'carbohydrates': '0.00'
            }
        )

        # Get the nutritional values in 1 unit of product
        response = self.client.get(
            reverse('api-ingredient-get-values', kwargs={'pk': 1}), {
                'amount': 1,
                'ingredient': 1,
                'unit': 2
            }
        )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf8'))
        self.assertEqual(len(result), 9)
        self.assertEqual(
            result, {
                'sodium': '0.61',
                'energy': '196.24',
                'energy_kilojoule': '821.07',
                'fat': '9.13',
                'carbohydrates_sugar': '0.00',
                'fat_saturated': '3.62',
                'fibres': '0.00',
                'protein': '28.58',
                'carbohydrates': '0.14'
            }
        )

    def test_calculate_value_anonymous(self):
        """
        Calculate the nutritional values as an anonymous user
        """

        self.calculate_value()

    def test_calculate_value_logged_in(self):
        """
        Calculate the nutritional values as a logged-in user
        """

        self.user_login('test')
        self.calculate_value()


class IngredientTestCase(WgerTestCase):
    """
    Tests other ingredient functions
    """

    def test_compare(self):
        """
        Tests the custom compare method based on values
        """
        language = Language.objects.get(pk=1)

        ingredient1 = Ingredient.objects.get(pk=1)
        ingredient2 = Ingredient.objects.get(pk=1)
        ingredient2.name = 'A different name altogether'
        self.assertFalse(ingredient1 == ingredient2)

        ingredient1 = Ingredient()
        ingredient1.name = 'ingredient name'
        ingredient1.energy = 150
        ingredient1.protein = 30
        ingredient1.language = language

        ingredient2 = Ingredient()
        ingredient2.name = 'ingredient name'
        ingredient2.energy = 150
        ingredient2.language = language
        self.assertFalse(ingredient1 == ingredient2)

        ingredient2.protein = 31
        self.assertFalse(ingredient1 == ingredient2)

        ingredient2.protein = None
        self.assertFalse(ingredient1 == ingredient2)

        ingredient2.protein = 30
        self.assertEqual(ingredient1, ingredient2)

        meal = Meal.objects.get(pk=1)
        self.assertFalse(ingredient1 == meal)

    def test_total_energy(self):
        """
        Tests the custom clean() method
        """
        self.user_login('admin')

        # Values OK
        ingredient = Ingredient()
        ingredient.name = 'FooBar, cooked, with salt'
        ingredient.energy = 50
        ingredient.protein = 0.5
        ingredient.carbohydrates = 12
        ingredient.fat = Decimal('0.1')
        ingredient.language_id = 1
        self.assertFalse(ingredient.full_clean())

        # Values wrong
        ingredient.protein = 20
        self.assertRaises(ValidationError, ingredient.full_clean)

        ingredient.protein = 0.5
        ingredient.fat = 5
        self.assertRaises(ValidationError, ingredient.full_clean)

        ingredient.fat = 0.1
        ingredient.carbohydrates = 20
        self.assertRaises(ValidationError, ingredient.full_clean)

        ingredient.fat = 5
        ingredient.carbohydrates = 20
        self.assertRaises(ValidationError, ingredient.full_clean)


class IngredientApiTestCase(api_base_test.ApiBaseResourceTestCase):
    """
    Tests the ingredient API resource
    """
    pk = 4
    resource = Ingredient
    private_resource = False
    overview_cached = True
    data = {'language': 1, 'license': 2}
