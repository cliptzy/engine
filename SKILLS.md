# Flet (flet.dev) Development Skills & Best Practices

## 1. Context & Role
You are an expert Python developer specializing in Flet (flet.dev). Flet is a framework that allows developers to build interactive multi-platform applications (Web, Desktop, Mobile) using pure Python, powered by Flutter under the hood. 

## 2. API Verification & Anti-Hallucination (CRITICAL)
*   **DO NOT GUESS:** Flet updates frequently. Do not rely solely on your pre-trained knowledge for API parameters, class names, or available properties.
*   **USE PROVIDED DOCS:** If running in Cursor or a similar environment, always prioritize the indexed documentation (e.g., `@FletDocs`) or files inside the `_docs/` directory of this workspace before generating code.
*   **SEARCH FIRST:** If you are unsure about the latest properties of a Flet control and have web search capabilities, search the official documentation at `https://flet.dev/docs/` before writing code.
*   **DEPRECATION AWARENESS:** Be aware that older patterns might be deprecated. Always prefer the modern approach (e.g., avoid `ft.UserControl` if standard component subclassing is the current standard).

## 3. Core Rules & Syntax
*   **Import Standard:** Always import Flet as `ft`.
    ```python
    import flet as ft
    ```
*   **Entry Point:** Every Flet app requires a `main` function that takes a `page` object of type `ft.Page`, and runs via `ft.app()`.
    ```python
    def main(page: ft.Page):
        # App logic here
        pass

    ft.app(target=main) # Add view=ft.AppView.WEB_BROWSER for web testing
    ```
*   **Adding Controls:** Use `page.add(control1, control2)` to append controls to the page and automatically update the UI.

## 4. State Management & UI Updates
*   **The `.update()` Rule:** Flet does NOT use reactive state variables by default. Whenever you modify a property of a control (e.g., changing a text value, changing a color), you MUST explicitly call `update()` on that control or `page.update()` to reflect the changes on the UI.
    ```python
    my_text = ft.Text(value="Initial")
    page.add(my_text)
    
    # Later in an event...
    my_text.value = "Updated"
    my_text.update() # CRITICAL: UI will not change without this
    ```

## 5. Event Handling
*   All event handler functions (e.g., for `on_click`, `on_change`, `on_submit`) must accept a single parameter: the event object, conventionally named `e`.
    ```python
    def button_clicked(e):
        page.add(ft.Text("Button was clicked!"))
        
    ft.ElevatedButton("Click me", on_click=button_clicked)
    ```

## 6. Layout & UI Composition
*   **Containers:** Use `ft.Container` for padding, margins, borders, and background colors.
*   **Flex Layout:** Use `ft.Row` and `ft.Column` to arrange elements. Use the `alignment` and `horizontal_alignment` / `vertical_alignment` properties to position items.
*   **Scrolling:** If a page or column will exceed the screen height, set `scroll=ft.ScrollMode.AUTO` or `scroll=ft.ScrollMode.ALWAYS`.

## 7. Routing & Navigation
*   For multi-page apps, do not just clear and add controls to the page. Use Flet's routing system with `page.views`.
*   Listen to `page.on_route_change` and `page.on_view_pop`.
*   Navigate using `page.go('/new-route')`.

## 8. Asynchronous Programming
*   Flet supports both sync and async functions. If the application involves network requests (like API calls) or heavy I/O, use `async def main(page: ft.Page):` and `ft.app(target=main)` still applies. 
*   Avoid using blocking calls like `time.sleep()` in the main thread; use `asyncio.sleep()` in async functions to prevent UI freezing.

## 9. Boilerplate Template
When asked to create a new Flet app, use this structure as your starting point:

```python
import flet as ft

def main(page: ft.Page):
    page.title = "Flet App"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    
    # Example state/control
    counter_text = ft.Text(value="0", size=30)
    
    # Example event handler
    def increment_click(e):
        current_val = int(counter_text.value)
        counter_text.value = str(current_val + 1)
        counter_text.update()

    # Build UI
    page.add(
        ft.Column(
            controls=[
                ft.Text("Welcome to Flet!", size=40, weight=ft.FontWeight.BOLD),
                counter_text,
                ft.ElevatedButton("Increment", on_click=increment_click)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
