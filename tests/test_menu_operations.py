import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.menu_operations import update_menu_item_price, add_operation_to_history


class TestMenuOperations(unittest.TestCase):

    @patch("utils.menu_operations.add_operation_to_history")
    def setUp(self, mock_add_history):
        # Mock connection and cursor for each test
        self.mock_db_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db_connection.cursor.return_value = self.mock_cursor

        # Mock the history function to avoid side effects
        self.mock_add_history = mock_add_history

    def test_update_menu_item_price(self):
        """
        Test that updating a menu item price works correctly.
        """
        # Set up test data
        item_id = 1
        new_price = 12.99

        # Call the function
        result, message = update_menu_item_price(
            item_id, new_price, self.mock_db_connection
        )

        # Check that the cursor execute method was called with the expected SQL
        self.mock_cursor.execute.assert_called_once()

        # Check that the connection commit method was called
        self.mock_db_connection.commit.assert_called_once()

        # Check that a success result was returned
        self.assertTrue(result)
        self.assertIn("updated successfully", message)

    def test_add_operation_to_history(self):
        """
        Test that operations are properly logged to history.
        """
        # Set up test data
        operation_type = "update_price"
        details = {"item_id": 1, "new_price": 12.99}
        status = "success"

        # Call the function
        add_operation_to_history(
            operation_type, details, status, self.mock_db_connection
        )

        # Check that the cursor execute method was called
        self.mock_cursor.execute.assert_called_once()

        # Check that the connection commit method was called
        self.mock_db_connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
