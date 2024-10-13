from langgraph.graph import StateGraph,START ,END
from src.Tools import *
from src.utilities import create_entry_node,Assistant,pop_dialog_state
from src.Pydantic_tools import *
from langchain_community.tools.tavily_search import TavilySearchResults
from src.route_tools import *
from src.prompt import *
from langchain_groq import ChatGroq

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint import memory







class Graphing:
    def __init__(self,llm):
        self.builder = StateGraph(State)
        self.llm=llm

    def user_info(self,state: State):
     
     return {"user_info": fetch_user_flight_information.invoke({})}

   
    def Tool_binding_llm_agent(self):
       #Flight binding Tools 
        #############################################################################################################
        #now after prmopt ham usko bound krdege
        self.update_flight_safe_tools = [search_flights]
        # isko ham use krege identify krne me which tool is sensitive and which tool is safe 
        self.update_flight_sensitive_tools = [update_ticket_to_new_flight, cancel_ticket]
        self.update_flight_tools = self.update_flight_safe_tools + self.update_flight_sensitive_tools

        #this tool runnable has been made and when use in the edge itv will ask as seperate assistant and user to answer teh question0
        self.update_flight_runnable = flight_booking_prompt | self.llm.bind_tools(
            self.update_flight_tools + [CompleteOrEscalate]
        )


        ########################################################################################################################
        # HOTEL Biniding
        self.book_hotel_safe_tools = [search_hotels]
        self.book_hotel_sensitive_tools = [book_hotel, update_hotel, cancel_hotel]
        self.book_hotel_tools = self.book_hotel_safe_tools + self.book_hotel_sensitive_tools
        self.book_hotel_runnable = book_hotel_prompt | self.llm.bind_tools(
            self.book_hotel_tools + [CompleteOrEscalate]
        )



        ###########################################################################################################################
        #BOOK CAR RENTAL TOOL BINDING

        self.book_car_rental_safe_tools = [search_car_rentals]
        self.book_car_rental_sensitive_tools = [
            book_car_rental,
            update_car_rental,
            cancel_car_rental,
        ]
        self.book_car_rental_tools =self.book_car_rental_safe_tools + self.book_car_rental_sensitive_tools
        self.book_car_rental_runnable = book_car_rental_prompt | self.llm.bind_tools(
            self.book_car_rental_tools + [CompleteOrEscalate]
        )

        ##########################################################################################################
        #BOOK EXCURSION
        self.book_excursion_safe_tools = [search_trip_recommendations]
        self.book_excursion_sensitive_tools = [book_excursion, update_excursion, cancel_excursion]
        self.book_excursion_tools = self.book_excursion_safe_tools + self.book_excursion_sensitive_tools
        self.book_excursion_runnable = book_excursion_prompt | self.llm.bind_tools(
            self.book_excursion_tools + [CompleteOrEscalate]
        )

        ###############################################################################################################

        #primary assitant 
        #isme ham  pydantic tools ass ker ge to llm ko pta chale ga ke kya tools krhe hain 
        self.primary_assistant_tools = [
            TavilySearchResults(max_results=1),
            search_flights,
            lookup_policy,
        ]
        self.assistant_runnable = primary_assistant_prompt | self.llm.bind_tools(
            self.primary_assistant_tools
            + [
                ToFlightBookingAssistant,
                ToBookCarRental,
                ToHotelBookingAssistant,
                ToBookExcursion,
            ]
        )

       
















    def Build(self):
        #yaha pe hamne user ki info fetch krli h or ab ham use tool calls agar hoi to usme pass krege 


        #starting of Our graph fetching all the info from db  at the starting
        self.builder.add_node("fetch_user_info", self.user_info)
        self.builder.add_edge(START, "fetch_user_info")

        # Flight booking assistant
        self.builder.add_node(
            "enter_update_flight",
            create_entry_node("Flight Updates & Booking Assistant", "update_flight"),
        )
        self.builder.add_node("update_flight", Assistant(self.update_flight_runnable))
        self.builder.add_edge("enter_update_flight", "update_flight")
        self.builder.add_node(
            "update_flight_sensitive_tools",
            create_tool_node_with_fallback(self.update_flight_sensitive_tools),
        )

        self.builder.add_node(
            "update_flight_safe_tools",
            create_tool_node_with_fallback(self.update_flight_safe_tools),
        )
        #         update flight
        #         ^          ^ 
        #        /            \
        #       /              \
        #    sensitive        safe Tools
        self.builder.add_edge("update_flight_sensitive_tools", "update_flight")
        self.builder.add_edge("update_flight_safe_tools", "update_flight")
        self.builder.add_conditional_edges(
            "update_flight",
            route_update_flight,
            ["update_flight_sensitive_tools", "update_flight_safe_tools", "leave_skill", END],
        )

        #    sensitive       safe Tools
        #        \            / 
        #         Condition -Router
        #            main             
        #            




        self.builder.add_node("leave_skill", pop_dialog_state)
        self.builder.add_edge("leave_skill", "primary_assistant")

        #Same for the Car.
        ######################################################################################



        self.builder.add_node(
            "enter_book_car_rental",
            create_entry_node("Car Rental Assistant", "book_car_rental"),
        )
        self.builder.add_node("book_car_rental", Assistant(self.book_car_rental_runnable))
        self.builder.add_edge("enter_book_car_rental", "book_car_rental")
        self.builder.add_node(
            "book_car_rental_safe_tools",
            create_tool_node_with_fallback(self.book_car_rental_safe_tools),
        )
        self.builder.add_node(
            "book_car_rental_sensitive_tools",
            create_tool_node_with_fallback(self.book_car_rental_sensitive_tools),
        )






        self.builder.add_edge("book_car_rental_sensitive_tools", "book_car_rental")
        self.builder.add_edge("book_car_rental_safe_tools", "book_car_rental")
        self.builder.add_conditional_edges(
            "book_car_rental",
            route_book_car_rental,
            [
                "book_car_rental_safe_tools",
                "book_car_rental_sensitive_tools",
                "leave_skill",
                END,
            ],
        )

        ##############################################################
        # Hotel booking assistant
        self.builder.add_node(
            "enter_book_hotel", create_entry_node("Hotel Booking Assistant", "book_hotel")
        )
        self.builder.add_node("book_hotel", Assistant(self.book_hotel_runnable))
        self.builder.add_edge("enter_book_hotel", "book_hotel")
        self.builder.add_node(
            "book_hotel_safe_tools",
            create_tool_node_with_fallback(self.book_hotel_safe_tools),
        )
        self.builder.add_node(
            "book_hotel_sensitive_tools",
            create_tool_node_with_fallback(self.book_hotel_sensitive_tools),
        )


        self.builder.add_edge("book_hotel_sensitive_tools", "book_hotel")
        self.builder.add_edge("book_hotel_safe_tools", "book_hotel")
        self.builder.add_conditional_edges(
            "book_hotel",
            route_book_hotel,
            ["leave_skill", "book_hotel_safe_tools", "book_hotel_sensitive_tools", END],
        )






        #########################################




        # Excursion assistant
        self.builder.add_node(
            "enter_book_excursion",
            create_entry_node("Trip Recommendation Assistant", "book_excursion"),
        )
        self.builder.add_node("book_excursion", Assistant(self.book_excursion_runnable))
        self.builder.add_edge("enter_book_excursion", "book_excursion")
        self.builder.add_node(
            "book_excursion_safe_tools",
            create_tool_node_with_fallback(self.book_excursion_safe_tools),
        )
        self.builder.add_node(
            "book_excursion_sensitive_tools",
            create_tool_node_with_fallback(self.book_excursion_sensitive_tools),
        )

        self.builder.add_edge("book_excursion_sensitive_tools", "book_excursion")
        self.builder.add_edge("book_excursion_safe_tools", "book_excursion")
        self.builder.add_conditional_edges(
            "book_excursion",
            route_book_excursion,
            ["book_excursion_safe_tools", "book_excursion_sensitive_tools", "leave_skill", END],
        )




        #########################
        #NOw primary assistan its little different 




        # Primary assistant
        self.builder.add_node("primary_assistant", Assistant(self.assistant_runnable))
        self.builder.add_node(
            "primary_assistant_tools", create_tool_node_with_fallback(self.primary_assistant_tools)
        )




        # The assistant can route to one of the delegated assistants,
        # directly use a tool, or directly respond to the user
        self.builder.add_conditional_edges(
            "primary_assistant",
            route_primary_assistant,
            [
                "enter_update_flight",
                "enter_book_car_rental",
                "enter_book_hotel",
                "enter_book_excursion",
                "primary_assistant_tools",
                END,
            ],
        )
        self.builder.add_edge("primary_assistant_tools", "primary_assistant")




        # bhai wapis bhi ana h main se to ye router bhi zaroori h 
        # Each delegated workflow can directly respond to the user
        # When the user responds, we want to return to the currently active workflow


        self.builder.add_conditional_edges("fetch_user_info", route_to_workflow)


        memory = MemorySaver()
        part_4_graph = self.builder.compile(
            checkpointer=memory,
            # Let the user approve or deny the use of sensitive tools
            interrupt_before=[
                "update_flight_sensitive_tools",
                "book_car_rental_sensitive_tools",
                "book_hotel_sensitive_tools",
                "book_excursion_sensitive_tools",
            ],
        )

        return part_4_graph

    














































