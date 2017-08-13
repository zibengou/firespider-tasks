from base import Spider, DataBase
import sys, getopt

if __name__ == '__main__':
    headers = {"authorization": "oauth c3cef7c66a1843f8b3a9e6a1e3160e20"}


    def combine_args(url_token, offset, limit, type=None):
        if type is None:
            user_params = {
                "include": "url_token,type,locations,name,description,business,employments,educations,answer_count,question_count,follower_count,following_count,headline,thanked_count,voteup_count,favorited_count,following_topic_count,following_favlists_count,participated_live_count,answer_count,articles_count"
            }
            path = "/api/v4/members/%(user)s" % {"user": url_token}
            params = user_params
        else:
            follow_params = {
                "include": "data[*].url_token,type,locations,name,description,business,employments,educations,answer_count,question_count,follower_count,following_count,headline,thanked_count,voteup_count,favorited_count,following_topic_count,following_favlists_count,participated_live_count,answer_count,articles_count",
                "offset": str(offset),
                "limit": str(limit)
            }
            path = "/api/v4/members/%(user)s/%(type)s" % {"user": url_token, "type": type}
            params = follow_params
        return path, params


    def get_user_list(url_token, type, offset=0, limit=20):
        path, params = combine_args(url_token, offset=offset, limit=limit, type=type)
        res = sp.get(path=path, params=params, headers=headers, is_json=True)
        if 'data' in res:
            res = res['data']
        else:
            res = []

        return res


    def find_next(name=None, type='followers', offset=0, limit=20):
        results = []
        if name is None:
            find_next_sql = "match(n:People) where n.%s is null and n.is_matching is null with n limit 1 set n.is_matching=True return n" % (
                type + "_matched")
        else:
            find_next_sql = "match(n:People{name:'%s',is_matching:False}) where n.%s is null return n limit 1" % (
                name, type + "_matched")
        data_list = db.execute(find_next_sql, arg=None)
        user = data_list[0]._values[0].properties
        counts = int(user['follower_count']) if type == 'followers' else int(user['following_count'])
        if counts < 1:
            return user, []
        else:
            counts = 2000 if counts > 2000 else counts
            for q_offset in range(offset, counts, limit):
                print("********* request user : %s total_counts : %s success_counts : %s *********" % (
                user['name'], str(counts), str(len(results))))
                results.extend(get_user_list(user['url_token'], type, q_offset, limit))
        return user, results


    def parse_user(user, url_token, type):
        args = {}
        user.pop('badge', None)

        def parse_business():
            sql = ''
            if 'business' in user:
                business = user['business']
                sql = ' merge(business:Business{name:{business}.name}) set business={business} merge(people)-[:work_in]->(business)'
                args['business'] = business
                user.pop('business', None)
            return sql

        def parse_locations():
            sql = ''
            if 'locations' in user:
                locations = user['locations']
                for index, location in enumerate(locations):
                    location_index_str = 'location_' + str(index) + '_v'
                    args[location_index_str] = location
                    sql += ' merge(%(loc_str)s:Location{name:{%(loc_str)s}.name}) set %(loc_str)s={%(loc_str)s} merge(people)-[:lived]->(%(loc_str)s)' % {
                        "loc_str": location_index_str}
                user.pop('locations', None)
            return sql

        def parse_educations():
            sql = ''
            if 'educations' in user:
                educations = user['educations']
                for index, education in enumerate(educations):
                    if 'school' not in education:
                        continue
                    if 'major' in education:
                        major = education['major']
                    else:
                        major = {"name": ""}
                    school = education['school']
                    school_index_str = 'school_' + str(index) + '_v'
                    args[school_index_str] = school
                    sql += ' merge(%(school_str)s:School{name:{%(school_str)s}.name}) set %(school_str)s={%(school_str)s} merge(people)-[:educated{major:"%(major)s"}]->(%(school_str)s)' % {
                        "school_str": school_index_str, "major": major['name']}
                user.pop('educations', None)
            return sql

        def parse_employments():
            sql = ''
            if 'employments' in user:
                employments = user['employments']
                for index, employment in enumerate(employments):
                    if 'company' not in employment:
                        continue
                    company = employment['company']
                    if 'job' in employment:
                        job = employment['job']
                    else:
                        job = {"name": ""}
                    company_index_str = 'company_' + str(index) + '_v'
                    args[company_index_str] = company
                    sql += ' merge(%(company_str)s:Company{name:{%(company_str)s}.name}) set %(company_str)s={%(company_str)s} merge(people)-[:work_for{job:"%(job)s"}]->(%(company_str)s)' % {
                        "company_str": company_index_str, "job": job['name']}
                user.pop('employments', None)
            return sql

        bus_sql = parse_business()
        loc_sql = parse_locations()
        edu_sql = parse_educations()
        emp_sql = parse_employments()
        relationship = 'follow_by' if type == 'followers' else 'following'
        sql = 'merge(people:People{url_token:{user}.url_token}) set people+={user} merge(xx:People{url_token:{url_token}}) merge(xx)-[:%s]->(people)' % relationship
        args['user'] = user
        args['url_token'] = url_token
        sql = sql + bus_sql + loc_sql + edu_sql + emp_sql
        return sql, args


    def insert(user, results, type='followers'):
        is_matching_sql = 'merge(xx:People{url_token:"%s"}) set xx.is_matching=True' % user['url_token']
        db.execute(is_matching_sql, arg=None)
        length = len(results)
        for index, result in enumerate(results):
            print("[%s/%s] insert user : %s" % (str(index + 1), str(length), result['name']))
            (sql, args) = parse_user(result, user['url_token'], type)
            db.execute(sql, **args)
        base_sql = 'merge(xx:People{url_token:"%s"}) set xx.%s=True set xx.is_matching=False' % (
            user['url_token'], type + "_matched")
        db.execute(base_sql, arg=None)


    opts, args = getopt.getopt(sys.argv[1:], ":t:n:")
    type = "followees"
    nums = 10
    for op, value in opts:
        if op == "-t":
            type = value
        elif op == "-n":
            nums = int(value)

    db = DataBase("neo4j", "2017", url="bolt://192.168.1.105:7687")
    sp = Spider("https://www.zhihu.com", verify=True)
    args_num = len(sys.argv)
    for i in range(0, nums):
        try:
            (user, results) = find_next(type=type)
            print("*********[%s/%s] parse user : %s *********" % (str(i + 1), str(nums), user['name']))
            insert(user, results, type=type)
        except Exception as e:
            print("*********[%s/%s] error parse : %s *********" % (str(i + 1), str(nums), str(e)))
            continue
    del db
    del sp
