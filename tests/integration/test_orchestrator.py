"""
Integration tests for the Orchestrator service.

Tests the end-to-end functionality of the Orchestrator and how it coordinates
between different services to process queries.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.orchestrator.orchestrator import Orchestrator


class TestOrchestratorIntegration:
    """Integration tests for the Orchestrator service."""

    def test_process_menu_query(self, mock_orchestrator):
        """Test processing a menu query end-to-end."""
        # Mock the query classification
        mock_orchestrator.classifier.classify_query.return_value = (
            "sql_query", 
            {"query_type": "menu_query"}
        )
        
        # Process a sample query
        result = mock_orchestrator.process_query("Show me all menu items at Idle Hour")
        
        # Verify the classifier was called
        mock_orchestrator.classifier.classify_query.assert_called_once()
        
        # Verify SQL generation was called
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        
        # Verify SQL execution was called
        mock_orchestrator.execution_service.execute_query.assert_called_once()
        
        # Verify response generation was called
        mock_orchestrator.response_generator.generate_response.assert_called_once()
        
        # Check the result structure
        assert "response" in result
        assert "query_type" in result
        assert "sql_query" in result
        assert "sql_result" in result
        assert result["query_type"] == "sql_query"
        assert result["response"] == "Here are the results for your query."

    def test_process_menu_update(self, mock_orchestrator):
        """Test processing a menu update query end-to-end."""
        # Mock the query classification for a price update
        mock_orchestrator.classifier.classify_query.return_value = (
            "menu_update", 
            {
                "query_type": "menu_update", 
                "update_type": "price_update", 
                "item_name": "Caesar Salad", 
                "new_price": 12.99
            }
        )
        
        # Process a sample query
        result = mock_orchestrator.process_query("Change the price of Caesar Salad to $12.99")
        
        # Verify the classifier was called
        mock_orchestrator.classifier.classify_query.assert_called_once()
        
        # Verify SQL generation was called with correct parameters
        mock_orchestrator.sql_generator.generate_sql.assert_called_once()
        
        # Verify SQL execution was called
        mock_orchestrator.execution_service.execute_query.assert_called_once()
        
        # Check the result structure
        assert "response" in result
        assert "query_type" in result
        assert "sql_query" in result
        assert "sql_result" in result
        assert result["query_type"] == "menu_update"
        assert "update_type" in result
        assert result["update_type"] == "price_update"

    def test_process_general_query(self, mock_orchestrator):
        """Test processing a general query that doesn't need SQL."""
        # Mock the query classification
        mock_orchestrator.classifier.classify_query.return_value = (
            "general", 
            {"query_type": "general"}
        )
        
        # Mock the generate_simple_response method
        with patch.object(mock_orchestrator, "_generate_simple_response") as mock_generate:
            mock_generate.return_value = "I can help you with that general query."
            
            # Process a sample query
            result = mock_orchestrator.process_query("What can you help me with?")
            
            # Verify the classifier was called
            mock_orchestrator.classifier.classify_query.assert_called_once()
            
            # Verify SQL generation was NOT called
            mock_orchestrator.sql_generator.generate_sql.assert_not_called()
            
            # Verify SQL execution was NOT called
            mock_orchestrator.execution_service.execute_query.assert_not_called()
            
            # Verify simple response generation was called
            mock_generate.assert_called_once()
            
            # Check the result structure
            assert "response" in result
            assert "query_type" in result
            assert result["query_type"] == "general"
            assert result["sql_query"] is None
            assert result["sql_result"] is None
            assert result["response"] == "I can help you with that general query."

    def test_conversation_history_management(self, mock_orchestrator):
        """Test that conversation history is properly maintained."""
        # Mock the query classification
        mock_orchestrator.classifier.classify_query.return_value = (
            "general", 
            {"query_type": "general"}
        )
        
        # Start with empty history
        mock_orchestrator.conversation_history = []
        
        # Mock the simple response generator
        with patch.object(mock_orchestrator, "_generate_simple_response") as mock_generate:
            mock_generate.return_value = "Response 1"
            
            # Process first query
            mock_orchestrator.process_query("Query 1")
            
            # Check history has user message and response
            assert len(mock_orchestrator.conversation_history) == 2
            assert mock_orchestrator.conversation_history[0]["role"] == "user"
            assert mock_orchestrator.conversation_history[0]["content"] == "Query 1"
            assert mock_orchestrator.conversation_history[1]["role"] == "assistant"
            assert mock_orchestrator.conversation_history[1]["content"] == "Response 1"
            
            # Process second query
            mock_generate.return_value = "Response 2"
            mock_orchestrator.process_query("Query 2")
            
            # Check history now has 4 messages
            assert len(mock_orchestrator.conversation_history) == 4
            assert mock_orchestrator.conversation_history[2]["content"] == "Query 2"
            assert mock_orchestrator.conversation_history[3]["content"] == "Response 2"

    def test_tts_response_processing(self, mock_orchestrator):
        """Test the text-to-speech response processing."""
        # Mock the text processing utilities
        with patch("services.utils.text_processing.clean_for_tts") as mock_clean:
            mock_clean.return_value = "Cleaned text for TTS"
            
            with patch("services.utils.text_processing.summarize_text") as mock_summarize:
                mock_summarize.return_value = "Summarized text for TTS"
                
                # Original response is longer than the max_tts_length
                original_response = "This is a long response " * 20
                mock_orchestrator.config["max_tts_length"] = 50
                
                tts_response = mock_orchestrator.get_tts_response(original_response)
                
                # Verify clean_for_tts was called
                mock_clean.assert_called_once_with(original_response)
                
                # Verify summarize_text was called
                mock_summarize.assert_called_once()
                
                # Check the result
                assert tts_response == "Summarized text for TTS"

    def test_location_setting(self, mock_orchestrator):
        """Test setting the restaurant location."""
        # Set a new location
        mock_orchestrator.set_location(61, "Pinetree Country Club")
        
        assert mock_orchestrator.current_location_id == 61
        assert mock_orchestrator.current_location_name == "Pinetree Country Club"
        
        # Process a query to verify location is used
        mock_orchestrator.classifier.classify_query.return_value = (
            "sql_query", 
            {"query_type": "menu_query"}
        )
        
        mock_orchestrator.process_query("Show me menu items")
        
        # Get the call arguments
        args, kwargs = mock_orchestrator.sql_generator.generate_sql.call_args
        
        # Verify location_id was included in the query info
        assert "location_id" in args[1]
        assert args[1]["location_id"] == 61 