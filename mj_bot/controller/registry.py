import asyncio
from inspect import iscoroutinefunction, signature
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, create_model


class RegisteredAction(BaseModel):
    """Model for a registered action"""

    name: str
    description: str
    function: Callable
    param_model: Type[BaseModel]

    def prompt_description(self) -> str:
        """Get a description of the action for the prompt"""
        skip_keys = ["title"]
        s = f"{self.description}: \n"
        s += "{" + str(self.name) + ": "
        s += str(
            {
                k: {
                    sub_k: sub_v for sub_k, sub_v in v.items() if sub_k not in skip_keys
                }
                for k, v in self.param_model.model_json_schema()["properties"].items()
            }
        )
        s += "}"
        return s


class ActionRegistry(BaseModel):
    """Model representing the action registry"""

    actions: dict[str, RegisteredAction] = {}

    def get_prompt_description(self, page=None) -> str:
        return "\n".join(
            action.prompt_description() for action in self.actions.values()
        )

        # filtered_actions = []
        # for action in self.actions.values():
        #     filtered_actions.append(action)
        # return "\n".join(action.prompt_description() for action in filtered_actions)


class ActionModel(BaseModel):
    pass


class Registry:
    def __init__(self):
        self.registry = ActionRegistry()

    def _create_param_model(self, function: Callable) -> Type[BaseModel]:
        """Creates a Pydantic model from function signature"""
        sig = signature(function)
        params = {
            name: (
                param.annotation,
                ... if param.default == param.empty else param.default,
            )
            for name, param in sig.parameters.items()
            if name != "browser"
            and name != "page_extraction_llm"
            and name != "available_file_paths"
        }
        # TODO: make the types here work
        return create_model(
            f"{function.__name__}_parameters",
            __base__=ActionModel,
            **params,  # type: ignore
        )

    def action(
        self,
        description: str,
        param_model: Optional[Type[BaseModel]] = None,
        domains: Optional[list[str]] = None,
        page_filter: Optional[Callable[[Any], bool]] = None,
    ):
        """Decorator for registering actions"""

        def decorator(func: Callable):
            # Skip registration if action is in exclude_actions
            # if func.__name__ in self.exclude_actions:
            #     return func

            # Create param model from function if not provided
            actual_param_model = param_model or self._create_param_model(func)

            # Wrap sync functions to make them async
            if not iscoroutinefunction(func):

                async def async_wrapper(*args, **kwargs):
                    return await asyncio.to_thread(func, *args, **kwargs)

                # Copy the signature and other metadata from the original function
                async_wrapper.__signature__ = signature(func)
                async_wrapper.__name__ = func.__name__
                async_wrapper.__annotations__ = func.__annotations__
                wrapped_func = async_wrapper
            else:
                wrapped_func = func

            action = RegisteredAction(
                name=func.__name__,
                description=description,
                function=wrapped_func,
                param_model=actual_param_model,
                # domains=domains,
                # page_filter=page_filter,
            )
            self.registry.actions[func.__name__] = action
            return func

        return decorator

    def get_prompt_description(self, page=None) -> str:
        """Get a description of all actions for the prompt

        If page is provided, only include actions that are available for that page
        based on their filter_func
        """
        return self.registry.get_prompt_description(page=page)
