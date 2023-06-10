from group_expenses_tool import create_group_expenses, app

group_name = "HH in Shuli Lutzi, TA 10/02/23"
user_ids = [1, 2, 3, 4, 5, 6, 7]

result = create_group_expenses(app, group_name, user_ids)
print(result)
