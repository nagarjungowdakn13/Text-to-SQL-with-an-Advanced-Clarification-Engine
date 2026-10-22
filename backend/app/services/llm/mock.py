import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.services.llm.base import LLMProvider, LLMProviderError
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)

class MockLLMProvider(LLMProvider):
    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name
        logger.info(f"Initialized MockLLMProvider with model {model_name}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        prompt_lower = prompt.lower()
        
        # Simulating SQL explanation requests
        if "explain" in prompt_lower or "result" in prompt_lower:
            return "Based on the database results, we found that total sales amount to $120,500. The highest-performing region is 'North America' with $60,200 in sales, followed by 'Europe' with $40,300. There are no notable anomalies in the retrieved customer transaction dataset."
        
        # Simulating SQL repair prompt
        if "repair" in prompt_lower or "syntax error" in prompt_lower:
            return "SELECT customer_id, SUM(total_amount) AS revenue FROM orders GROUP BY customer_id ORDER BY revenue DESC LIMIT 5;"
            
        return "This is a mock text generation response from QueryPilot's Mock LLM Provider."

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> T:
        prompt_lower = prompt.lower()
        model_name = response_model.__name__

        # Extract the exact user question between quotes to completely avoid template instruction collisions
        query_text = prompt_lower
        if 'user question:\n"' in prompt_lower:
            try:
                query_text = prompt_lower.split('user question:\n"')[1].split('"')[0]
            except Exception:
                pass
        elif 'clarified user query:\n"' in prompt_lower:
            try:
                query_text = prompt_lower.split('clarified user query:\n"')[1].split('"')[0]
            except Exception:
                pass

        logger.debug(f"Mock structured generation requested for model: {model_name}. Isolated Query: {query_text}")

        try:
            # Let's inspect the target response model and return realistic mocked data.
            if "Ambiguity" in model_name or "Clarification" in model_name:
                # If the test query contains "stubborn", keep it ambiguous to test loop prevention limits
                if "stubborn" in query_text:
                    data = {
                        "is_ambiguous": True,
                        "ambiguity_score": 0.95,
                        "ambiguity_type": "metric",
                        "clarification_question": "How should I define 'best customer'?",
                        "options": [
                            "Highest lifetime value (total revenue)",
                            "Highest number of orders placed"
                        ],
                        "suggested_safest_assumption": "Highest lifetime value (total revenue)",
                        "reasoning": "Stubborn mock trigger for loop tests."
                    }
                # If the query has already been clarified or has an assumption, it is no longer ambiguous!
                elif "clarified" in query_text or "assuming" in query_text or "assumed" in query_text:
                    data = {
                        "is_ambiguous": False,
                        "ambiguity_score": 0.1,
                        "ambiguity_type": "none",
                        "clarification_question": "",
                        "options": [],
                        "suggested_safest_assumption": "",
                        "reasoning": "The query has been clarified by conversational inputs."
                    }
                # Mock ambiguity detection responses
                elif "best customer" in query_text:
                    data = {
                        "is_ambiguous": True,
                        "ambiguity_score": 0.95,
                        "ambiguity_type": "metric",
                        "clarification_question": "How should I define 'best customer'?",
                        "options": [
                            "Highest lifetime value (total revenue)",
                            "Highest number of orders placed",
                            "Highest average order value (AOV)"
                        ],
                        "suggested_safest_assumption": "Highest lifetime value (total revenue)",
                        "reasoning": "The term 'best customer' is highly subjective. It could mean highest total purchase amount, highest volume of orders, or other business loyalty metrics."
                    }
                elif "sales" in query_text and not any(k in query_text for k in ["region", "month", "product"]):
                    data = {
                        "is_ambiguous": True,
                        "ambiguity_score": 0.85,
                        "ambiguity_type": "metric",
                        "clarification_question": "How should we aggregate sales performance?",
                        "options": [
                            "Total revenue generated",
                            "Number of individual items sold",
                            "Overall order count",
                            "Net profit margins"
                        ],
                        "suggested_safest_assumption": "Total revenue generated",
                        "reasoning": "The user asked for 'sales perform' without specifying if they meant gross revenue, order volume, or net profits."
                    }
                elif "active users" in query_text or "active customer" in query_text:
                    data = {
                        "is_ambiguous": True,
                        "ambiguity_score": 0.78,
                        "ambiguity_type": "filter",
                        "clarification_question": "What activity threshold determines if a user/customer is 'active'?",
                        "options": [
                            "Placed an order within the last 30 days",
                            "Placed an order within the last 90 days",
                            "Logged in within the last 7 days",
                            "Created an account within the last 30 days"
                        ],
                        "suggested_safest_assumption": "Placed an order within the last 30 days",
                        "reasoning": "An 'active user' or 'active customer' can be defined by login frequency or by transactional purchases within varied time ranges."
                    }
                else:
                    # Straightforward queries, no ambiguity
                    data = {
                        "is_ambiguous": False,
                        "ambiguity_score": 0.15,
                        "ambiguity_type": "none",
                        "clarification_question": "",
                        "options": [],
                        "suggested_safest_assumption": "",
                        "reasoning": "The intent is clear and fits the schema directly."
                    }
                return response_model.model_validate(data)

            elif "SQL" in model_name or "Plan" in model_name:
                # Mock SQL Generation responses
                if "best customer" in query_text:
                    # Let's check if the user clarified order count or average order value
                    if "order" in query_text:
                        sql = "SELECT c.customer_id, c.first_name, c.last_name, COUNT(o.order_id) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER BY order_count DESC LIMIT 5;"
                        intent = "Find top customers by number of orders placed"
                    else:
                        sql = "SELECT c.customer_id, c.first_name, c.last_name, SUM(o.total_amount) AS revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER BY revenue DESC LIMIT 5;"
                        intent = "Find top customers by total spending (revenue)"
                elif "active" in query_text:
                    sql = "SELECT customer_id, first_name, last_name, email FROM customers WHERE last_order_date >= NOW() - INTERVAL '30 days';"
                    intent = "Retrieve customers active in the last 30 days"
                elif "product" in query_text:
                    sql = "SELECT product_name, category, price FROM products ORDER BY price DESC LIMIT 10;"
                    intent = "Get the 10 most expensive products"
                else:
                    sql = "SELECT * FROM customers LIMIT 10;"
                    intent = "List the first 10 customers"
                
                data = {
                    "intent": intent,
                    "tables": ["customers", "orders"] if "customer" in query_text or "best" in query_text else ["products"],
                    "columns": ["customer_id", "first_name", "last_name", "total_amount"] if "customer" in query_text else ["product_name", "category", "price"],
                    "filters": ["last_order_date >= NOW() - INTERVAL '30 days'"] if "active" in query_text else [],
                    "joins": ["customers JOIN orders ON customers.customer_id = orders.customer_id"] if "customer" in query_text or "best" in query_text else [],
                    "aggregations": ["SUM(total_amount)"] if "revenue" in query_text or "best" in query_text else [],
                    "order_by": ["revenue DESC"] if "best" in query_text else [],
                    "limit": 5 if "best" in query_text else 10,
                    "sql": sql,
                    "assumptions": ["Assuming best customer is defined by total sales volume"] if "best" in query_text and "order" not in query_text else [],
                    "confidence": 0.9
                }
                return response_model.model_validate(data)

            elif "Explain" in model_name or "Explanation" in model_name:
                data = {
                    "summary": "Here is the breakdown of top customers based on total spending. John Doe spent a total of $5,400, followed by Jane Smith with $4,850.",
                    "insights": ["Highest spending customer is John Doe.", "Top 5 customers represent 24% of total sales."],
                    "anomalies": [],
                    "confidence_score": 0.95
                }
                return response_model.model_validate(data)
                
            else:
                # Default validation fallback
                raise ValueError(f"Mock provider does not support model {model_name}")

        except Exception as e:
            logger.error(f"Error in Mock structured generation: {e}")
            raise LLMProviderError(f"Mock generation failed for {model_name}: {e}")
