-- EducaChat: perfil do aluno (série) vinculado ao usuário do Supabase Auth.
-- Aplicar no SQL Editor do projeto Supabase (ou via `supabase db push`).
--
-- Garantias:
--  * a série só é gravada no cadastro (trigger) ou uma única vez via POST /perfil;
--  * o usuário lê apenas o próprio perfil (RLS);
--  * não há policy de UPDATE/DELETE: o aluno não consegue trocar a própria série.

create table if not exists public.perfis (
    user_id   uuid primary key references auth.users (id) on delete cascade,
    ano       smallint not null check (ano between 6 and 9),
    criado_em timestamptz not null default now()
);

alter table public.perfis enable row level security;

revoke all on public.perfis from anon;
revoke all on public.perfis from authenticated;
grant select, insert on public.perfis to authenticated;

create policy perfil_select_proprio on public.perfis
    for select to authenticated
    using (user_id = (select auth.uid()));

create policy perfil_insert_proprio on public.perfis
    for insert to authenticated
    with check (user_id = (select auth.uid()));

-- Cria o perfil no momento do cadastro a partir de raw_user_meta_data.ano.
-- user_metadata pode ser editado depois pelo usuário, mas este trigger só roda no INSERT
-- em auth.users; a fonte de verdade da série é public.perfis.
create or replace function public.criar_perfil_no_cadastro()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_ano int;
begin
    begin
        v_ano := (new.raw_user_meta_data ->> 'ano')::int;
    exception when others then
        v_ano := null;
    end;
    if v_ano between 6 and 9 then
        insert into public.perfis (user_id, ano) values (new.id, v_ano)
        on conflict (user_id) do nothing;
    end if;
    return new;
end;
$$;

drop trigger if exists ao_criar_usuario on auth.users;
create trigger ao_criar_usuario
    after insert on auth.users
    for each row execute function public.criar_perfil_no_cadastro();
