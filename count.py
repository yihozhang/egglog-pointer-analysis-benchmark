import csv

s = set()
with open('cclyzerpp-out/unification.var_points_to_final.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for row in reader:
        # print(row)
        # break
        s.add(row[-1])
print(len(s))
# print(s)
