from group_expenses_tool import create_group_expenses, app

group_name = input("Please enter a group name: ")

# Input user ids as comma-separated values
user_ids_string = input("Please enter user IDs separated by commas: ")

# Convert user_ids_string to a list of integers
user_ids = [int(id_str) for id_str in user_ids_string.split(',')]

result = create_group_expenses(app, group_name, user_ids)
print(result)
