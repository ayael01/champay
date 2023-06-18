from group_expenses_tool import delete_group_expenses, list_groups, app

with app.app_context():
    list_groups()
    group_id = input("Please enter the group ID to delete: ")
    print(delete_group_expenses(app, int(group_id)))
