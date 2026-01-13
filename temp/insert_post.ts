import { type TPostFileMeta } from '@repo/markdown-parsing/src/types';
import { QueryTypes, Sequelize, Transaction } from 'sequelize';

export const insertPost = async (
    db: Sequelize,
    meta: TPostFileMeta,
    tx: Transaction
) => {
    const results = (await db.query(
        `
        INSERT INTO 
            posts (id, user_id, title, content, status, created_at, updated_at, slug, category_id, group_id)
        VALUES 
            (:id, :userId, :title, :content, :status, NOW(), NOW(), :slug, :categoryId, :groupId)
        RETURNING id
    `,
        {
            replacements: {
                id: meta.id,
                groupId: meta.id,
                slug: meta.slug,
                userId: meta.userId,
                title: meta.title,
                content: meta.content,
                status: meta.status || 'public',
                categoryId: meta.categoryId,
            },
            type: QueryTypes.SELECT,
            transaction: tx,
        }
    )) as Array<{ id: number }>;

    const insertedId = results[0]?.id;
    console.log('>> meta.id:', meta.id);
    console.log(`>> Inserted post: ${insertedId}`);
    return insertedId;
};
