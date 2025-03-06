#include <stdio.h>
#include <ctype.h>
#include <stdbool.h>

#define AC 0
#define WA 1
#define PE 2
#define ERROR -1

int spj(
    FILE *tc_input,
    FILE *tc_output,
    FILE *user_output);

void close_file(FILE *f)
{
    if (f != NULL)
    {
        fclose(f);
    }
}

int main(int argc, char *args[])
{
    int result = ERROR;

    if (argc != 4)
    {
        printf("Usage: spj tc.in tc.out user.out\n");
        return result;
    }

    FILE *tc_input = fopen(args[1], "r");
    FILE *tc_output = fopen(args[2], "r");
    FILE *user_output = fopen(args[3], "r");

    if (tc_input == NULL || tc_output == NULL || user_output == NULL)
    {
        printf("Failed to open file\n");
    }
    else
    {
        result = spj(tc_input, tc_output, user_output);
        printf("Result: %d\n", result);
    }

    close_file(tc_input);
    close_file(tc_output);
    close_file(user_output);

    return result;
}

bool is_space_char(int c)
{
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
}

void compare_until_nonspace(
    int &c_std,
    int &c_usr,
    FILE *&fd_std,
    FILE *&fd_usr, int &ret)
{
    while (isspace(c_std) || isspace(c_usr))
    {
        if (c_std != c_usr)
        {
            if (c_std == EOF || c_usr == EOF)
            {
                return;
            }
            if (c_std == '\r' && c_usr == '\n')
            {
                c_std = fgetc(fd_std);
                if (c_std != c_usr)
                    ret = PE;
            }
            else
            {
                ret = PE;
            }
        }
        if (isspace(c_std))
            c_std = fgetc(fd_std);
        if (isspace(c_usr))
            c_usr = fgetc(fd_usr);
    }
}

int spj(
    FILE *tc_input,
    FILE *tc_output,
    FILE *user_output)
{
    int ret = AC;
    int c_std, c_usr;

    c_std = fgetc(tc_output);
    c_usr = fgetc(user_output);
    
    while (true)
    {
        compare_until_nonspace(
            c_std,
            c_usr,
            tc_output,
            user_output,
            ret);
        while (!isspace(c_std) || !isspace(c_usr))
        {
            if (c_std == EOF && c_usr == EOF)
                return ret;
            if (c_std == EOF || c_usr == EOF)
            {
                FILE *fd_tmp;
                if (c_std == EOF)
                {
                    if (!is_space_char(c_usr))
                    {
                        ret = WA;
                        return ret;
                    }
                    fd_tmp = user_output;
                }
                else
                {
                    if (!is_space_char(c_std))
                    {
                        ret = WA;
                        return ret;
                    }
                    fd_tmp = tc_output;
                }
                int c;
                while ((c = fgetc(fd_tmp)) != EOF)
                {
                    if (c == '\r')
                        c = '\n';
                    if (!is_space_char(c))
                    {
                        ret = WA;
                        return ret;
                    }
                }
                return ret;
            }
            if (c_std != c_usr)
            {
                ret = WA;
                return ret;
            }
            c_std = fgetc(tc_output);
            c_usr = fgetc(user_output);
        }
    }
}
